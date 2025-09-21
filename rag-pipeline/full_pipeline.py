import subprocess
import sys
import os
import argparse


def run_script(label, path_to_script, years):
    print(f"\n🟡 Running: {label}")
    try:
        subprocess.run(
            [sys.executable, path_to_script, "--years"] + [str(y) for y in years],
            check=True
        )
        print(f"✅ Completed: {label}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed during: {label}")
        print(e)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", nargs="+", type=int, required=True, help="List of years to process")
    args = parser.parse_args()
    years = args.years

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    SCRAPING_SCRIPT = os.path.join(BASE_DIR, "scrappers", "lu_scrapper", "main.py")
    CLEANING_SCRIPT = os.path.join(BASE_DIR, "cleaning", "main.py")
    EMBEDDING_SCRIPT = os.path.join(BASE_DIR, "chunking_and_embedding", "main.py")

    run_script("📦 Pipeline 1: Scraping, Upload, Transform", SCRAPING_SCRIPT, years)
    run_script("🧼 Pipeline 2: OCR, Clean, Merge", CLEANING_SCRIPT, years)
    run_script("🧠 Pipeline 3: Chunking + Embedding + Upload", EMBEDDING_SCRIPT, years)

    print("\n🎉 All pipelines completed successfully!")

if __name__ == "__main__":
    main()
