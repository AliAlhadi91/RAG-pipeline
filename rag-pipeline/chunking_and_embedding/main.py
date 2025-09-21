import argparse
import shutil
import download_from_s3
import semantic_chunking
import embed_chunks
import upload_vectors

def run_pipeline(years):
    for year in years:
        print(f"\n📥 Downloading files for {year}...")
        download_from_s3.run(year)

        print(f"\n🧠 Running semantic chunking for {year}...")
        semantic_chunking.run(year)

        print(f"\n📌 Embedding chunks for {year}...")
        embed_chunks.run(year)

        print(f"\n☁️ Uploading vectors for {year}...")
        upload_vectors.run(year)

        print(f"\n🧹 Cleaning up temporary and output folders for {year}...")
        for folder in [
            f"temp_{year}",
            f"{year}_semantic_chunking_titan",
            f"{year}_chunked_embedded_gemini",
            f"{year}_chunked_embedded_updated"
        ]:
            shutil.rmtree(folder, ignore_errors=True)

    print("\n✅ All years processed and cleaned up successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", nargs="+", type=int, required=True)
    args = parser.parse_args()
    run_pipeline(args.years)
