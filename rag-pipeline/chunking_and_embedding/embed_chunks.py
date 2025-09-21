import os
import json
import time
from pathlib import Path
from tqdm import tqdm
import google.generativeai as genai
from utilities import settings


# Get secrets safely
genai_api_key = settings.GENAI_API_KEY

def run(year: int):
    input_root = Path(f"{year}_semantic_chunking_titan")
    output_root = Path(f"{year}_chunked_embedded_gemini")
    model_id = "models/gemini-embedding-001"
    max_tokens_estimate = 8192  # Gemini's upper token limit

    genai.configure(api_key=genai_api_key)
    output_root.mkdir(parents=True, exist_ok=True)

    def embed_gemini(text, retries=5, delay=2):
        if len(text.split()) > 5000:
            print("⚠️ Skipping very long chunk (~5000+ words)")
            return None

        for attempt in range(retries):
            try:
                response = genai.embed_content(
                    model=model_id,
                    content={"parts": [{"text": text}]},
                    task_type="retrieval_document"
                )
                return response["embedding"]
            except Exception as e:
                print(f"❌ Attempt {attempt+1}: Gemini embedding failed: {e}")
                time.sleep(delay * (attempt + 1))  # exponential backoff

        return None

    all_files = list(input_root.rglob("*.json"))
    for input_path in tqdm(all_files, desc=f"Embedding {year} ({len(all_files)} files)"):
        rel_path = input_path.relative_to(input_root)
        output_path = output_root / rel_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        failed_count = 0
        for idx, entry in enumerate(data):
            if "chunk" not in entry:
                continue
            if "embedding" in entry:
                continue  # already embedded

            emb = embed_gemini(entry["chunk"])
            if emb is not None:
                data[idx]["embedding"] = emb
            else:
                failed_count += 1

        with open(output_path, "w", encoding="utf-8") as out:
            json.dump(data, out, ensure_ascii=False, indent=2)

        if failed_count:
            print(f"⚠️ {failed_count} chunks failed in {input_path.name}")

    print("✅ Embedding complete.")
