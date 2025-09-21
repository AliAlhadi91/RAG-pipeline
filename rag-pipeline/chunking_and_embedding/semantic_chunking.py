import os
import json
import re
from typing import List
import numpy as np
#from tqdm import tqdm
import boto3
from utilities import settings

def run(year: int):
    

    input_root = f"temp_{year}"
    output_root = f"{year}_semantic_chunking_titan"
    metadata_path = f"./enriched_rulings/rulings_{year}.json"

    bedrock = boto3.client("bedrock-runtime", region_name=settings.REGION_NAME)

    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata_list = json.load(f)

    def extract_id(entry):
        match = re.search(r'ID=(\d+)', entry.get("link", ""))
        if match:
            return match.group(1)
        match = re.search(r'/(\d+)\.pdf', entry.get("s3_pdf_path", ""))
        if match:
            return match.group(1)
        return None

    metadata_dict = {
        extract_id(entry): entry for entry in metadata_list if extract_id(entry) is not None
    }

    def split_into_sentences(text: str) -> List[str]:
        return [s.strip() for s in re.split(r'(?<=[.؟!])\s+', text) if s.strip()]

    def split_long_sentence(sentence: str, limit=settings.SUBCHUNK_TOKEN_LIMIT) -> List[str]:
        words = sentence.split()
        if len(words) <= limit:
            return [sentence]
        return [' '.join(words[i:i+limit]) for i in range(0, len(words), limit)]

    def create_sliding_windows(subchunks: List[str], window_size: int) -> List[str]:
        return [' '.join(subchunks[i:i+window_size]) for i in range(len(subchunks) - window_size + 1)]

    def embed_text_titan(text: str) -> np.ndarray:
        try:
            response = bedrock.invoke_model(
                modelId=settings.MODEL_ID,
                body=json.dumps({"inputText": text}),
                contentType="application/json",
                accept="application/json"
            )
            body = json.loads(response["body"].read())
            return np.array(body["embedding"])
        except Exception as e:
            print(f"❌ Failed to embed with Titan: {text[:30]}... — {e}")
            return np.zeros(1536)  # Titan v2 output dim

    def compute_distances(windows: List[str]) -> List[float]:
        embeddings = [embed_text_titan(text) for text in windows]
        distances = []
        for i in range(len(embeddings) - 1):
            a, b = embeddings[i], embeddings[i + 1]
            sim = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8)
            distances.append(1 - sim)
        return distances

    def find_breakpoints(distances: List[float], percentile: float) -> List[int]:
        threshold = np.percentile(distances, percentile)
        return [i for i, d in enumerate(distances) if d > threshold]

    def group_by_breakpoints(subchunks: List[str], breakpoints: List[int], window_size: int) -> List[str]:
        final_chunks = []
        indices = [0] + [bp + window_size for bp in breakpoints if bp + window_size < len(subchunks)] + [len(subchunks)]
        for i in range(len(indices) - 1):
            group = subchunks[indices[i]:indices[i+1]]
            final_chunks.append(' '.join(group))
        return final_chunks

    def enforce_token_limit(chunks: List[str], limit=settings.FINAL_CHUNK_TOKEN_LIMIT) -> List[str]:
        final = []
        for chunk in chunks:
            words = chunk.split()
            if len(words) <= limit:
                final.append(chunk)
            else:
                for i in range(0, len(words), limit):
                    final.append(' '.join(words[i:i + limit]))
        return final

    def process_file(file_path: str, doc_id: str, out_path: str):
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()

        sentences = split_into_sentences(text)
        subchunks = []
        for sent in sentences:
            subchunks.extend(split_long_sentence(sent))

        windows = create_sliding_windows(subchunks,settings.WINDOW_SIZE)
        if len(windows) < 2:
            return

        distances = compute_distances(windows)
        breakpoints = find_breakpoints(distances, settings.BREAKPOINT_PERCENTILE)
        chunks = group_by_breakpoints(subchunks, breakpoints, settings.WINDOW_SIZE)
        final_chunks = enforce_token_limit(chunks)

        meta = metadata_dict.get(doc_id, {})
        output = []
        for idx, chunk in enumerate(final_chunks):
            output.append({
                "index": idx,
                "chunk": chunk,
                "link": meta.get("link", ""),
                "title": meta.get("title", ""),
                "full_document": doc_id,
                "list": meta.get("list", [])
            })

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

    for root, _, files in os.walk(input_root):
        for file in files:
            if file.endswith(".txt"):
                full_path = os.path.join(root, file)
                doc_id = os.path.splitext(file)[0]
                rel_path = os.path.relpath(full_path, input_root)
                out_path = os.path.join(output_root, os.path.splitext(rel_path)[0] + ".json")
                process_file(full_path, doc_id, out_path)
