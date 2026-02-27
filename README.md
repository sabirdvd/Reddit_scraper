# Reddit Scraper

### Run Scraper

Scrape all apps:

```bash
python reddit_scraper.py
```

This scrapes all configured apps and saves JSON/CSV files under `output/`.

Scrape by category:

```bash
python reddit_scraper.py -c "Communication" "Productivity"
```

List available categories:

```bash
python reddit_scraper.py --list-categories
```

Scrape specific apps:

```bash
python reddit_scraper.py -a "Google Drive" "TikTok Studio" Uber
```

Optional flags:

```bash
python reddit_scraper.py --max-posts 100 --delay 2 --outdir output
```

## Quality Check

```bash
python data_quality_check.py --outdir output
```

Strict mode (non-zero exit on issues):

```bash
python data_quality_check.py --outdir output --strict
```
