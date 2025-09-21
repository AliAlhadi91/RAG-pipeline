import os
from pathlib import Path

def run(year: int):
    source_base = Path(f"{year}_ocr")
    target_base = Path(f"{year}_ocr_full")
    target_base.mkdir(parents=True, exist_ok=True)

    for folder in sorted(source_base.iterdir()):
        if not folder.is_dir(): continue

        txt_files = sorted(
            [f for f in folder.glob("*.txt") if f.stem.isdigit()],
            key=lambda x: int(x.stem)
        )

        if not txt_files:
            print(f"⚠️ No txt files found in {folder.name}")
            continue

        merged_text = ""
        for txt_file in txt_files:
            content = txt_file.read_text(encoding="utf-8")
            merged_text += content.strip() + "\n\n"

        out_folder = target_base / folder.name
        out_folder.mkdir(parents=True, exist_ok=True)
        out_path = out_folder / f"{folder.name}.txt"
        out_path.write_text(merged_text.strip(), encoding="utf-8")

        print(f"✅ Merged {len(txt_files)} files into: {out_path}")
