import boto3
import os
from pathlib import Path
from utilities import settings

def run(year: int):
    prefix = f"{year}/"
    temp_dir = Path(f"temp_{year}")
    temp_dir.mkdir(parents=True, exist_ok=True)

    s3 = boto3.client("s3")

    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=settings.DEST_BUCKET, Prefix=prefix)

    print(f"📥 Downloading images for year {year}...")

    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.lower().endswith(".jpg"):
                continue

            local_path = temp_dir / Path(key).relative_to(prefix)
            local_path.parent.mkdir(parents=True, exist_ok=True)

            print(f"⬇️ {key} → {local_path}")
            s3.download_file(settings.DEST_BUCKET, key, str(local_path))

    print(f"✅ Download complete for {year}. Saved to {temp_dir}\n")