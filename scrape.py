"""Download raw datasets from the Uzbekistan National Statistics Committee (stat.uz).

Every dataset listed in datasets.csv is fetched as JSON from the committee's
open-data API and saved unchanged to data/raw/<section>/<id>.json.
"""

import json
import time
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://api.siat.stat.uz/media/uploads/sdmx/sdmx_data_{id}.json"
RAW_DIR = Path("data/raw")
DELAY_SECONDS = 1.0  # be polite to the server
RETRIES = 3

session = requests.Session()
session.headers["User-Agent"] = "uzbekistan-stats-scraper (github.com)"


def fetch(dataset_id: int) -> dict | list:
    url = BASE_URL.format(id=dataset_id)
    for attempt in range(1, RETRIES + 1):
        try:
            response = session.get(url, timeout=60)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as error:
            if attempt == RETRIES:
                raise
            print(f"  attempt {attempt} failed ({error}); retrying...")
            time.sleep(5 * attempt)


def main() -> None:
    datasets = pd.read_csv("datasets.csv")
    failures = []

    for row in datasets.itertuples(index=False):
        print(f"[{row.section}] {row.id}: {row.title}")
        try:
            payload = fetch(row.id)
        except Exception as error:  # keep going; report at the end
            print(f"  FAILED: {error}")
            failures.append(row.id)
            continue

        out_path = RAW_DIR / row.section / f"{row.id}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        time.sleep(DELAY_SECONDS)

    print(f"\nDownloaded {len(datasets) - len(failures)} of {len(datasets)} datasets.")
    if failures:
        print(f"Failed IDs: {failures}")
    if len(failures) == len(datasets):
        raise SystemExit("Every download failed.")


if __name__ == "__main__":
    main()
