# Uzbekistan Statistics: Investments and Prices

*A lil experiment with scraping data from stat.uz.*

Official statistics of Uzbekistan on **investments in fixed capital** (19 datasets) and **prices and price indexes** (79 datasets), downloaded from the National Statistics Committee ([stat.uz](https://stat.uz/en)) and cleaned into tidy CSV tables.

## Data

| Path | Contents |
|---|---|
| `data/catalog.csv` | One row per dataset: title, unit, periodicity, last update, row count, year range, source URL |
| `data/clean/investments.csv` | All investment datasets stacked in one table |
| `data/clean/prices.csv` | All price datasets stacked in one table |
| `data/clean/<section>/<id>.csv` | One tidy table per dataset |
| `data/raw/<section>/<id>.json` | Original files, unchanged |

Clean tables are in **long format**: one row per item and period.

| Column | Meaning |
|---|---|
| `code` | Statistical classifier code (e.g. `1700` = Republic of Uzbekistan) |
| `name_en`, `name_ru`, `name_uz`, `name_uz_cyrillic` | Region or item name in each language |
| `period` | Period as published (`2024`, `2024-01`, ...) |
| `year` | Year of the period |
| `value` | Numeric value |
| `dataset_id`, `dataset_title`, `unit` | Added in the stacked section tables |

## Cleaning steps

1. Reshape from wide (one column per period) to long format.
2. Standardise column names to `snake_case`.
3. Convert values to numbers (handles `1 234,5`-style formatting); drop missing markers such as `-` and `…`.
4. Trim stray whitespace in names; remove duplicate rows.
5. Record each dataset's metadata in `data/catalog.csv`.

## How it runs

`scrape.py` downloads every dataset listed in `datasets.csv` from the committee's open-data API; `clean.py` builds the tidy tables. A GitHub Actions workflow (`.github/workflows/scrape.yml`) runs both and commits the results. Re-run it any time from the **Actions** tab, or uncomment the `schedule` line for monthly updates.

To run locally:

```bash
pip install -r requirements.txt
python scrape.py
python clean.py
```

To add datasets, add rows to `datasets.csv` (the ID is the number in each dataset's download link on stat.uz).

## Source and license

Source: National Statistics Committee of the Republic of Uzbekistan, [stat.uz](https://stat.uz/en). The data is published under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/); reuse must credit stat.uz.
