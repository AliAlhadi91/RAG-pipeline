import os
import json
import uuid
import boto3
from pathlib import Path
from weaviate import WeaviateClient
from weaviate.connect import ConnectionParams
from utilities import settings

# === CONFIGURATION ===


# === AWS client ===
s3 = boto3.client("s3", region_name=settings.AWS_REGION)

# === Weaviate client ===
conn_params = ConnectionParams.from_url(
    url=settings.WEAVIATE_URL,
    grpc_port=50051
)
client = WeaviateClient(connection_params=conn_params)
client.connect()
collection = client.collections.get(settings.CLASS_NAME)

# === Upload full JSON file to S3 ===
def upload_json_to_s3(year, file_nb, file_path):
    key = f"{year}/{file_nb}/{file_nb}.json"
    try:
        s3.upload_file(str(file_path), settings.CHUNK_BUCKET, key)
        return f"s3://{settings.CHUNK_BUCKET}/{key}"
    except Exception as e:
        print(f"❌ Failed to upload JSON {key}: {e}")
        return None

# === Upload each JSON file to Weaviate ===
def process_json_file(file_path, year):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to read {file_path}: {e}")
        return

    parts = file_path.parts
    if len(parts) < 3 or not parts[-3] == f"{year}_chunked_embedded_gemini":
        return

    file_nb = parts[-2]
    file_path_str = f"{year}/{file_nb}"

    # Upload full JSON file to S3
    s3_url = upload_json_to_s3(year, file_nb, file_path)
    if not s3_url:
        return

    for item in data:
        emb = item.get("embedding", [])
        if not isinstance(emb, list) or len(emb) != settings.EXPECTED_DIM:
            print(f"⚠️ Skipped invalid embedding in {file_path} — index {item.get('index')}")
            continue

        obj = {
            "chunk": item.get("chunk"),
            "link": item.get("link"),
            "title": item.get("title"),
            "list":item.get("list"),
            "full_document": item.get("full_document"),
            "path": file_path_str,
            "index": item.get("index")
        }

        uid = uuid.uuid5(uuid.NAMESPACE_DNS, f"{obj['full_document']}_{obj['index']}")

        try:
            collection.data.insert(
                properties=obj,
                vector=emb,
                uuid=str(uid)
            )
        except Exception as e:
            print(f"❌ Failed to insert into Weaviate: {e}")

# === Entrypoint ===
def run(year: int):
    input_dir = Path(f"{year}_chunked_embedded_gemini")
    if not input_dir.exists():
        print(f"❌ Folder not found: {input_dir}")
        return

    json_files = list(input_dir.rglob("*.json"))
    print(f"📂 Found {len(json_files)} JSON files in {input_dir}...")

    for file_path in json_files:
        process_json_file(file_path, year)

    print(f"✅ Completed upload for year {year}.")
