import os
import glob
import json
import requests
import argparse
from urllib.parse import urlparse, parse_qs
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from concurrent.futures import ThreadPoolExecutor, as_completed
from utilities import settings
import sys
import os

# Add the project root to Python path to resolve `utilities/`
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ==== CONFIGURATION ====


# ==== INIT S3 CLIENT ====
session = boto3.Session(
    profile_name=settings.AWS_PROFILE,
    region_name=settings.AWS_REGION
)
s3 = session.client("s3")


# ==== UTILITY FUNCTIONS ====

def extract_doc_id_from_url(url):
    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        return query.get("RuliID", [None])[0]
    except:
        return None


def upload_to_s3(pdf_content, year, doc_id):
    try:
        s3_key = f"{year}/{doc_id}.pdf"
        s3.put_object(
            Bucket=settings.S3_BUCKET,
            Key=s3_key,
            Body=pdf_content,
            ContentType="application/pdf"
        )
        print(f"✅ Uploaded PDF: s3://{settings.S3_BUCKET}/{s3_key}")
        return f"s3://{settings.S3_BUCKET}/{s3_key}"
    except (BotoCoreError, ClientError) as e:
        print(f"❌ S3 error for {doc_id}: {e}")
        return None


def upload_enriched_json_to_s3(filepath, year):
    try:
        filename = os.path.basename(filepath)
        s3_key = f"{year}/{filename}"
        with open(filepath, "rb") as data_file:
            s3.upload_fileobj(data_file, settings.S3_BUCKET, s3_key)
        print(f"☁️ Uploaded enriched JSON: s3://{settings.S3_BUCKET}/{s3_key}")
    except (BotoCoreError, ClientError) as e:
        print(f"❌ Failed to upload enriched JSON: {e}")


def download_pdf(url):
    for _ in range(settings.MAX_RETRIES):
        try:
            r = requests.get(url, headers=settings.HEADERS, timeout=10)
            if r.status_code == 200:
                return r.content
        except Exception:
            continue
    print(f"❌ Failed to download PDF: {url}")
    return None


def process_file(filepath, year):
    filename = os.path.basename(filepath)

    print(f"\n📄 Processing: {filename}")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    def process_entry(entry):
        pdf_url = entry.get("link_to_full_document")
        if not pdf_url:
            return None

        doc_id = extract_doc_id_from_url(pdf_url)
        if not doc_id:
            print(f"⚠️ Skipping: can't extract RuliID from {pdf_url}")
            return None

        pdf_content = download_pdf(pdf_url)
        if not pdf_content:
            return None

        s3_path = upload_to_s3(pdf_content, year, doc_id)
        entry["s3_pdf_path"] = s3_path
        return entry

    enriched_data = []

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(process_entry, entry): entry for entry in data}

        for future in as_completed(futures):
            result = future.result()
            if result:
                enriched_data.append(result)
            else:
                enriched_data.append(futures[future])  # Preserve entry even if failed

    # Save enriched file
    os.makedirs(settings.OUTPUT_FOLDER, exist_ok=True)
    output_path = os.path.join(settings.OUTPUT_FOLDER, filename)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(enriched_data, f, ensure_ascii=False, indent=2)

    print(f"💾 Enriched file saved: {output_path}")

    # Upload enriched JSON to S3
    upload_enriched_json_to_s3(output_path, year)


# ==== MAIN with year argument ====
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True, help="Year to process")
    args = parser.parse_args()
    year = args.year

    input_file = f"rulings_{year}.json"
    if not os.path.exists(input_file):
        print(f"❌ File not found: {input_file}")
    else:
        process_file(input_file, year)
