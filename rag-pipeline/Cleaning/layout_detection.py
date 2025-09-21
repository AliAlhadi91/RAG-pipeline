# run_serverless.py
import os
import json
import time
import base64
from pathlib import Path
from typing import List, Tuple, Set
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from PIL import Image
from io import BytesIO
from utilities import settings

# =======================
# CONFIG — EDIT THESE
# =======================
AWS_REGION = settings.AWS_REGION
ENDPOINT_NAME = settings.LAYOUT_ENDPOINT_NAME
THRESHOLD = 0.8
# =======================

# Match your original label map (IDs must match what your model returns)
label_names = {
    1: 'Header', 2: 'Table', 3: 'footer', 4: 'image', 5: 'text', 6: 'title'
}
split_order = ['title', 'text', 'Table', 'footer', 'image']

runtime = boto3.client("sagemaker-runtime", region_name=AWS_REGION)

def invoke_endpoint_image_bytes(img: Image.Image, threshold: float = THRESHOLD) -> dict:
    """
    Sends the image as JSON (base64) to the endpoint and returns parsed JSON.
    (Switch to application/x-image if you prefer raw bytes.)
    """
    buf = BytesIO()
    img.save(buf, format="JPEG")  # or "PNG" if your images are PNG
    img_bytes = buf.getvalue()

    payload = {
        "image": base64.b64encode(img_bytes).decode("utf-8"),
        "threshold": float(threshold)
    }

    resp = runtime.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        ContentType="application/json",
        Body=json.dumps(payload).encode("utf-8")
    )
    body = resp["Body"].read().decode("utf-8")
    return json.loads(body)

def convert_predictions_for_pipeline(resp_json: dict) -> List[Tuple[List[int], int, float]]:
    """
    Convert server response -> list of (box, label_id, score) like your local code expected.
    Response format assumed:
      {"predictions":[{"box":[x1,y1,x2,y2],"label_id":6,"label":"title","score":0.93}, ...]}
    """
    out = []
    for det in resp_json.get("predictions", []):
        box = [int(v) for v in det["box"]]
        label_id = int(det.get("label_id", 0))
        score = float(det.get("score", 0.0))
        out.append((box, label_id, score))
    return out

def sort_and_merge(predictions: List[Tuple[List[int], int, float]], image_width: int):
    x_split = image_width / 3
    group1, group2, group3 = [], [], []
    for item in predictions:
        box, label, score = item
        if label in {1, 3, 4}:  # skip Header, footer, image
            continue
        x1, y1, x2, y2 = map(int, box)
        mid_x = (x1 + x2) / 2
        image_center = image_width / 2
        if abs(mid_x - image_center) <= 300 and (abs(x2 - x1) < 300 or abs(x2 - x1) > 800):
            group3.append(item)
        elif x1 > x_split:
            group1.append(item)
        else:
            group2.append(item)

    group1.sort(key=lambda x: x[0][1])
    group2.sort(key=lambda x: x[0][1])
    group3.sort(key=lambda x: x[0][1])

    merged, i, j, g3_idx = [], 0, 0, 0
    while i < len(group1):
        g1_y1 = group1[i][0][1]
        while g3_idx < len(group3) and group3[g3_idx][0][1] < g1_y1:
            g3_y1 = group3[g3_idx][0][1]
            while j < len(group2) and group2[j][0][1] < g3_y1:
                merged.append(group2[j]); j += 1
            merged.append(group3[g3_idx]); g3_idx += 1
        merged.append(group1[i]); i += 1

    merged += group2[j:]
    merged += group3[g3_idx:]

    groups_present: Set[int] = {1 if group1 else None, 2 if group2 else None, 3 if group3 else None} - {None}
    return merged, groups_present

def run(year: int):
    base_folder = Path(f"temp_{year}")
    if not base_folder.exists():
        print(f"Folder not found: {base_folder}")
        return

    for folder in sorted(base_folder.iterdir()):
        if not folder.is_dir():
            continue

        image_files = sorted(
            [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg')) and f.split('.')[0].isdigit()],
            key=lambda x: int(x.split('.')[0])
        )

        for img_name in image_files:
            image_path = folder / img_name
            print(f"📂 Processing: {image_path}")

            image_pil = Image.open(image_path).convert('RGB')
            image_width, image_height = image_pil.size

            # ====== Inference via Serverless Endpoint ======
            try:
                resp = invoke_endpoint_image_bytes(image_pil, threshold=THRESHOLD)
            except (ClientError, BotoCoreError) as e:
                print(f"❌ Invoke failed for {img_name}: {e}")
                continue

            # Convert + client-side filter (keeps behavior identical to your local code)
            predictions_full = convert_predictions_for_pipeline(resp)
            predictions = [(b, l, s) for (b, l, s) in predictions_full if s >= THRESHOLD and l != 1]

            # ====== Same 2-col vs 1-col logic ======
            predictions, groups_present = sort_and_merge(predictions, image_width)
            is_two_column = not (groups_present <= {1, 3} or groups_present <= {2, 3})

            if is_two_column:
                print(f"🟥 2-column detected in {img_name}")
                sorted_preds = sorted(
                    [p for p in predictions if label_names.get(p[1], '') in split_order],
                    key=lambda x: split_order.index(label_names.get(x[1], ''))
                )

                # Replace original with cropped parts
                image_path.unlink(missing_ok=True)
                two_col_folder = folder / Path(img_name).stem
                if two_col_folder.exists():
                    for f in two_col_folder.iterdir():
                        try: f.unlink()
                        except Exception: pass
                else:
                    two_col_folder.mkdir(parents=True, exist_ok=True)

                for crop_idx, (box, label_id, _) in enumerate(sorted_preds, 1):
                    x1, y1, x2, y2 = map(int, box)
                    cropped = image_pil.crop((x1, y1, x2, y2))
                    cropped.save(two_col_folder / f"{crop_idx}.jpg")
            else:
                print(f"🟩 1-column: keeping full image {img_name}")
                # just re-save (no change)
                image_pil.save(image_path)


