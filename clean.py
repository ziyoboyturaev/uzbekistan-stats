"""Turn the raw stat.uz JSON files into tidy CSV tables.

Raw files are "wide": one row per region or item, one column per period.
This script reshapes each one to "long" format (one row per item and period),
standardises column names, converts values to numbers, and writes:

  data/clean/<section>/<id>.csv   one tidy table per dataset
  data/clean/<section>.csv        all datasets of a section stacked together
  data/catalog.csv                one row per dataset with its metadata
"""

import json
import re
from pathlib import Path

import pandas as pd

RAW_DIR = Path("data/raw")
CLEAN_DIR = Path("data/clean")
PERIOD_COLUMN = re.compile(r"^\d{4}")  # "2010", "2024-01", "2024 I chorak", ...

RENAME = {
    "Code": "code",
    "Klassifikator": "name_uz",
    "Klassifikator_ru": "name_ru",
    "Klassifikator_en": "name_en",
    "Klassifikator_uzc": "name_uz_cyrillic",
}
MISSING_MARKERS = {"", "-", "–", "—", "…", "...", "x", "X", "nan", "None", "null"}


def snake_case(text: str) -> str:
    text = re.sub(r"[^0-9a-zA-Z]+", "_", str(text)).strip("_").lower()
    return text or "column"


def to_number(value):
    """Convert '1 234,5' / '104.2' / '-' to a float or None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(" ", "").replace(" ", "")
    if text in MISSING_MARKERS:
        return None
    text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def unpack(payload) -> tuple[list, list]:
    """Return (metadata, data) whatever the outer wrapping looks like."""
    if isinstance(payload, list) and payload and isinstance(payload[0], dict) and "data" in payload[0]:
        payload = payload[0]
    if isinstance(payload, dict):
        return payload.get("metadata", []) or [], payload.get("data", []) or []
    return [], payload if isinstance(payload, list) else []


def metadata_dict(metadata: list) -> dict:
    """Flatten the metadata list to {english name: english value}."""
    result = {}
    for item in metadata:
        if isinstance(item, dict):
            key = item.get("name_en") or item.get("name_uz")
            value = item.get("value_en") or item.get("value_uz")
            if key:
                result[str(key).strip()] = value
    return result


def find_meta(meta: dict, *words: str):
    for key, value in meta.items():
        if any(word in key.lower() for word in words):
            return value
    return None


def tidy(data: list) -> pd.DataFrame:
    wide = pd.DataFrame(data)
    if wide.empty:
        return wide
    period_cols = [c for c in wide.columns if PERIOD_COLUMN.match(str(c))]
    id_cols = [c for c in wide.columns if c not in period_cols]

    long = wide.melt(id_vars=id_cols, value_vars=period_cols, var_name="period", value_name="value")
    long = long.rename(columns={c: RENAME.get(c, snake_case(c)) for c in id_cols})

    long["period"] = long["period"].astype(str).str.strip()
    long["year"] = long["period"].str[:4].astype(int)
    long["value"] = long["value"].map(to_number)
    long = long.dropna(subset=["value"])

    text_cols = [c for c in long.columns if c not in ("period", "year", "value")]
    for col in text_cols:
        long[col] = long[col].map(lambda v: re.sub(r"\s+", " ", str(v)).strip() if pd.notna(v) else v)

    ordered = text_cols + ["period", "year", "value"]
    return long[ordered].drop_duplicates().reset_index(drop=True)


def main() -> None:
    datasets = pd.read_csv("datasets.csv")
    catalog, stacks = [], {}

    for row in datasets.itertuples(index=False):
        raw_path = RAW_DIR / row.section / f"{row.id}.json"
        if not raw_path.exists():
            print(f"skip {row.id}: no raw file")
            continue

        metadata, data = unpack(json.loads(raw_path.read_text(encoding="utf-8")))
        meta = metadata_dict(metadata)
        table = tidy(data)
        unit = find_meta(meta, "unit", "measure")

        out_path = CLEAN_DIR / row.section / f"{row.id}.csv"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(out_path, index=False)

        if not table.empty:
            stacked = table.copy()
            stacked.insert(0, "dataset_title", row.title)
            stacked.insert(0, "dataset_id", row.id)
            stacked["unit"] = unit
            stacks.setdefault(row.section, []).append(stacked)

        catalog.append({
            "dataset_id": row.id,
            "section": row.section,
            "title": row.title,
            "unit": unit,
            "periodicity": find_meta(meta, "periodicity", "frequency"),
            "last_modified": find_meta(meta, "last modified"),
            "rows": len(table),
            "first_year": table["year"].min() if not table.empty else None,
            "last_year": table["year"].max() if not table.empty else None,
            "source_url": f"https://api.siat.stat.uz/media/uploads/sdmx/sdmx_data_{row.id}.json",
        })
        print(f"{row.id}: {len(table)} rows")

    for section, frames in stacks.items():
        pd.concat(frames, ignore_index=True).to_csv(CLEAN_DIR / f"{section}.csv", index=False)

    pd.DataFrame(catalog).to_csv("data/catalog.csv", index=False)
    print(f"\nCleaned {len(catalog)} datasets.")


if __name__ == "__main__":
    main()
