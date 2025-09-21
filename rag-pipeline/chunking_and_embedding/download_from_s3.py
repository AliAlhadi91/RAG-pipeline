import os
import boto3
from botocore.exceptions import ClientError
from utilities import settings

def run(year: int):
    prefix = f"{year}/"
    local_dir = f"temp_{year}"

    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.bucket_name_cleaned, Prefix=prefix):
        for obj in page.get("Contents", []):
            rel_path = obj["Key"]
            if rel_path.endswith("/"):
                continue
            local_path = os.path.join(local_dir, os.path.relpath(rel_path, prefix))
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            try:
                s3.download_file(settings.bucket_name_cleaned, rel_path, local_path)
                #print(f"✅ Downloaded {rel_path}")
            except ClientError as e:
                print(f"❌ Failed to download {rel_path}: {e}")