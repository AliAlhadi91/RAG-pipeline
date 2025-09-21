import argparse
import shutil
from pathlib import Path

from download_from_s3 import run as download_from_s3
from layout_detection import run as layout_detection
from ocr import run as run_ocr
from filter_by_confidence import run as filter_by_confidence
from merge import run as merge_texts
from clean_and_upload import run as clean_and_upload

def process_year(year):
    print(f"\n========================\n🗓️ Processing Year: {year}\n========================")

    download_from_s3(year)
    layout_detection(year)
    run_ocr(year)
    # filter_by_confidence(year)
    merge_texts(year)
    clean_and_upload(year)

    for folder in [f"temp_{year}", f"{year}_ocr", f"{year}_ocr_full", f"{year}_ocr_cleaned"]:
        p = Path(folder)
        if p.exists():
            print(f"🧹 Removing {folder}")
            shutil.rmtree(p, ignore_errors=True)

def main(years):
    for year in years:
        process_year(year)
    print("\n🎉 Cleaning pipeline completed for all years!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", nargs="+", type=int, required=True)
    args = parser.parse_args()
    main(args.years)
