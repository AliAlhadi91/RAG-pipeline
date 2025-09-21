import os, subprocess, argparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

def run_script(label, script_name, year):
    script_path = os.path.join(BASE_DIR, script_name)
    print(f"➡️ Running {label} for {year}")
    subprocess.run(
        ["python", script_path, "--year", str(year)],
        cwd=PROJECT_ROOT,  # 👈 runs from top level so `utilities` is visible
        check=True
    )

def main(years):
    for year in years:
        run_script("scraping", "scrapping.py", year)
        run_script("upload", "upload_to_s3.py", year)
        run_script("transform", "transform.py", year)
    print("✅ Done")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", nargs="+", type=int, required=True)
    args = parser.parse_args()
    main(args.years)
