import csv
import shutil
from pathlib import Path
from collections import defaultdict

def run(year: int):
    csv_path = Path("ocr_confidence_summary.csv")
    original_base = Path(f"{year}_ocr")
    low_conf_folder = Path(f"{year}_ocr_low_confidence")
    low_conf_folder.mkdir(parents=True, exist_ok=True)

    folder_confidences = defaultdict(list)

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            rel_path, conf = row
            conf = float(conf)
            folder_name = Path(rel_path).parts[0]
            folder_confidences[folder_name].append(conf)

    for folder_name, confs in folder_confidences.items():
        if any(c >= 0.8 for c in confs):
            print(f"✅ Keeping {folder_name} (has confidence ≥ 0.8)")
        else:
            source = original_base / folder_name
            dest = low_conf_folder / folder_name

            if source.exists():
                print(f"📦 Moving {folder_name} → {dest}")
                shutil.move(str(source), str(dest))
            else:
                print(f"⚠️ Folder not found: {source}")
