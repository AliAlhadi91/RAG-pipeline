import boto3
import os
from pathlib import Path
from helper import CamelTextPreProcessor
from camel_tools.utils.dediac import dediac_ar
from utilities import settings
import sys



def preprocess_text_file(input_path: Path, output_path: Path, use_morph: bool = False):
    preprocessor = CamelTextPreProcessor(remove_all_prefix=True, remove_all_suffix=True)
    text = input_path.read_text(encoding='utf-8')
    cleaned = preprocessor.clean(text)
    normalized = preprocessor.normalize(cleaned)
    normalized_special = preprocessor.normalize_special_characters(normalized)
    dediac = dediac_ar(normalized_special)

    tokens = (
        preprocessor.morphologically_tokenize(dediac)
        if use_morph else
        preprocessor.simple_tokenize(dediac)
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(" ".join(tokens), encoding='utf-8')
    print(f"✅ Cleaned: {input_path} → {output_path}")

def run(year: int, use_morph: bool = False):
    input_root = Path(f"{year}_ocr_full")
    output_root = Path(f"{year}_ocr_cleaned")

    s3 = boto3.client("s3")

    txt_files = list(input_root.rglob("*.txt"))

    for txt_file in txt_files:
        relative_path = txt_file.relative_to(input_root)
        output_path = output_root / relative_path

        # Clean and save
        preprocess_text_file(txt_file, output_path, use_morph=use_morph)

        # Upload to S3
        s3_key = f"{year}/{relative_path.as_posix()}"
        print(f"⬆️ Uploading: {output_path} → s3://{settings.bucket_name_cleaned}/{s3_key}")
        s3.upload_file(str(output_path), settings.bucket_name_cleaned, s3_key)

    print(f"\n🎉 Cleaned and uploaded all files for year {year}.")
