# Reddit Scraper

### Reddit Scraper (Modes)

Use one of these depending on what you want to collect:

1. Scrape all configured apps (normal settings)
```bash
python reddit_scraper.py
```

2. List categories and aliases
```bash
python reddit_scraper.py --list-categories
```

3. Scrape by categories (supports names and aliases)
```bash
python reddit_scraper.py -c "Share photos & videos" Communication
python reddit_scraper.py -c social productivity
```

4. Scrape selected apps only
```bash
python reddit_scraper.py -a "Google Drive" "TikTok Studio" Uber
```

5. Custom limits/output directory
```bash
python reddit_scraper.py -c communication --max-posts 100 --delay 1.5 --outdir output
```

Output is saved as JSON and CSV under `output/<category>/`.

### Reddit Scraper (Flags)

1. `-a`, `--app`: Scrape specific apps only.
2. `-c`, `--categories`: Scrape by category.
3. `--list-categories`: List categories and exit.
4. `--max-posts`: Max posts per app source (default: `200`).
5. `--delay`: Delay between requests in seconds (default: `2.0`).
6. `--outdir`: Output directory for JSON/CSV (default: `output`).

## Quality Check

```bash
python data_quality_check.py --outdir output
```

Strict mode (non-zero exit on issues):

```bash
python data_quality_check.py --outdir output --strict
```

### Flags (`data_quality_check.py`)

- `--outdir`: Root output folder to scan (default: `output`).
- `--strict`: Exit non-zero when shape/duplicate URL issues are found.
