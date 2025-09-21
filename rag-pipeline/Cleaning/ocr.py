import os
import csv
import json
import boto3
from pathlib import Path
from google.cloud import documentai_v1 as documentai
from google.protobuf.json_format import MessageToDict
from utilities import settings
from credentials import GCP_OCR_CRED
# ocr.py
from google.cloud import documentai_v1 as documentai
from google.oauth2 import service_account

# GCP_OCR_CRED must be a Python dict with the service-account JSON fields
creds = service_account.Credentials.from_service_account_info(GCP_OCR_CRED)

client = documentai.DocumentProcessorServiceClient(credentials=creds)


def run(year: int):

    input_base = Path(f"temp_{year}")
    output_base = Path(f"{year}_ocr")
    csv_path = Path("ocr_confidence_summary.csv")

    # os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(GCP_OCR_CRED)
    # client = documentai.DocumentProcessorServiceClient()
    processor_name = client.processor_path(settings.project_id, settings.location, settings.processor_id)

    s3 = boto3.client("s3")

    csv_rows = [("image_path", "average_confidence")]

    def get_mime_type(file_path: Path):
        ext = file_path.suffix.lower()
        if ext == ".png": return "image/png"
        elif ext in {".jpg", ".jpeg"}: return "image/jpeg"
        else: raise ValueError(f"Unsupported file type: {ext}")

    def process_image(image_path: Path):
        try:
            with open(image_path, "rb") as f:
                content = f.read()
            mime_type = get_mime_type(image_path)
            raw_document = documentai.RawDocument(content=content, mime_type=mime_type)
            response = client.process_document(request={"name": processor_name, "raw_document": raw_document})
            document = response.document
            text = document.text or ""
            confidences = [token.layout.confidence for page in document.pages for token in page.tokens]
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            return text, avg_conf, document
        except Exception as e:
            print(f"❌ Failed to process {image_path}: {e}")
            return "", 0.0, None

    for folder in sorted(input_base.iterdir()):
        if not folder.is_dir(): continue

        out_folder = output_base / folder.name
        out_folder.mkdir(parents=True, exist_ok=True)

        for item in sorted(folder.iterdir()):
            if item.is_file() and item.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                text, avg_conf, doc = process_image(item)
                if text:
                    (out_folder / f"{item.stem}.txt").write_text(text, encoding="utf-8")
                    if doc:
                        json_path = out_folder / f"{item.stem}.json"
                        with open(json_path, "w", encoding="utf-8") as jf:
                            json.dump(MessageToDict(doc._pb), jf, ensure_ascii=False, indent=2)
                        # Upload JSON to S3
                        s3_key = f"{year}/{folder.name}/{json_path.name}"
                        print(f"⬆️ Uploading JSON to s3://{settings.s3_bucket_ocr}/{s3_key}")
                        s3.upload_file(str(json_path), settings.s3_bucket_ocr, s3_key)
                    rel_path = out_folder / f"{item.stem}.txt"
                    csv_rows.append((str(rel_path.relative_to(output_base)), round(avg_conf, 4)))

            elif item.is_dir():
                part_texts, part_confidences, part_docs = [], [], []
                for part in sorted(item.glob("*.[pj][pn]g")):
                    text, conf, doc = process_image(part)
                    if text: part_texts.append(text)
                    if conf > 0: part_confidences.append(conf)
                    if doc: part_docs.append(doc)
                if part_texts:
                    merged_text = "\n\n".join(part_texts)
                    (out_folder / f"{item.name}.txt").write_text(merged_text, encoding="utf-8")
                    merged_json_path = out_folder / f"{item.name}.json"
                    with open(merged_json_path, "w", encoding="utf-8") as jf:
                        json.dump([MessageToDict(d._pb) for d in part_docs], jf, ensure_ascii=False, indent=2)
                    # Upload JSON to S3
                    s3_key = f"{year}/{folder.name}/{merged_json_path.name}"
                    print(f"⬆️ Uploading JSON to s3://{settings.s3_bucket_ocr}/{s3_key}")
                    s3.upload_file(str(merged_json_path), settings.s3_bucket_ocr, s3_key)
                    avg_conf = sum(part_confidences) / len(part_confidences) if part_confidences else 0.0
                    csv_rows.append((f"{folder.name}/{item.name}.txt", round(avg_conf, 4)))

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(csv_rows)

    print(f"\n✅ OCR complete for {year}. Confidence summary saved to: {csv_path}\n")
