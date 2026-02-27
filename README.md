# Reddit Scraper

## Run

```bash
python reddit_scraper.py
```

This scrapes all configured apps and saves JSON/CSV files under `output/`.

## Quality Check

```bash
python data_quality_check.py --outdir output
```

Strict mode (non-zero exit on issues):

```bash
python data_quality_check.py --outdir output --strict
```
