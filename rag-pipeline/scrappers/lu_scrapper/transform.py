import os
import io
import boto3
import logging
import argparse
from pdf2image import convert_from_bytes
from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor, as_completed
from utilities import settings
import sys
import os

# Add the project root to Python path to resolve `utilities/`
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)



# ==== CONFIGURATION ====


# ==== SETUP LOGGING ====
logging.basicConfig(
    filename=settings.LOG_FILE,
    filemode='a',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ==== INIT BOTO3 SESSION ====
session = boto3.Session(
    profile_name=settings.PROFILE_NAME,
    region_name=settings.REGION_NAME
)
s3 = session.client("s3")


def list_pdfs_in_year(bucket, year):
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, Prefix=f"{year}/")

    files = []
    for page in pages:
        for obj in page.get('Contents', []):
            key = obj['Key']
            if key.endswith(".pdf"):
                files.append(key)
    return files


def download_pdf(bucket, key):
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        return response['Body'].read()
    except ClientError as e:
        msg = f"Download failed: {key} -> {e}"
        print(msg)
        logging.error(msg)
        return None


def upload_images(images, year, file_base):
    for i, image in enumerate(images):
        try:
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='JPEG')
            img_buffer.seek(0)
            key = f"{year}/{file_base}/{i+1}.jpg"
            s3.put_object(
                Bucket=settings.DEST_BUCKET,
                Key=key,
                Body=img_buffer,
                ContentType='image/jpeg'
            )
        except Exception as e:
            msg = f"Upload failed: {year}/{file_base}/{i+1}.jpg -> {e}"
            print(msg)
            logging.error(msg)


def process_pdf(key):
    year = key.split('/')[0]
    file_base = os.path.splitext(os.path.basename(key))[0]

    pdf_bytes = download_pdf(settings.SOURCE_BUCKET, key)
    if not pdf_bytes:
        return

    try:
        images = convert_from_bytes(pdf_bytes)
    except Exception as e:
        msg = f"Conversion failed: {key} -> {e}"
        print(msg)
        logging.error(msg)
        return

    upload_images(images, year, file_base)


def main(year):
    print(f"🔍 Processing PDFs from year: {year}")

    try:
        pdfs = list_pdfs_in_year(settings.SOURCE_BUCKET, str(year))
    except Exception as e:
        msg = f"Listing PDFs failed for year {year}: {e}"
        print(msg)
        logging.error(msg)
        return

    if not pdfs:
        print(f"⚠️ No PDFs found for year {year}")
        return

    print(f"▶️ Found {len(pdfs)} PDFs in {year}. Starting processing...")

    with ThreadPoolExecutor(max_workers=settings.MAX_WORKERS) as executor:
        futures = [executor.submit(process_pdf, key) for key in pdfs]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logging.error(f"Unhandled exception in worker: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True, help="Year to process from S3")
    args = parser.parse_args()

    main(args.year)
