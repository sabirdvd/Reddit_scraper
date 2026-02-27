# reddit_scraper (mode) 
# a) Scrape all configured apps (normal settings)
#    python reddit_scraper.py
# b) List categories and aliases
#    python reddit_scraper.py --list-categories
# c) Scrape by categories (supports names and aliases)
#    python reddit_scraper.py -c "Share photos & videos" Communication
#    python reddit_scraper.py -c social productivity
# d) Scrape selected apps only
#    python reddit_scraper.py -a "Google Drive" "TikTok Studio" Uber
# f) Custom limits/output directory
#    python reddit_scraper.py -c communication --max-posts 100 --delay 1.5 --outdir output

# reddit_scraper (flag)   
# 1) -a, --app: Scrape specific apps only.
# 2) -c, --categories : Scrape by category.
# 3) --list-categories: List categories and exit.
# 4) --max-posts : Max posts per app source (default: 200).
# 5) --delay : Delay between requests in seconds (default: 2.0).
# 6) --outdir : Output directory for JSON/CSV (default: output).


import argparse
import requests
import json
import csv
import time
import os
import re
from urllib.parse import urljoin
from requests.exceptions import RequestException

UA_BROWSER = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

MAX_REDDIT_PAGE_SIZE = 100
DEFAULT_MAX_POSTS = 200
DEFAULT_DELAY_SECONDS = 2.0
DEFAULT_OUTDIR = "output"
MAX_RETRIES = 3


def norm_app(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())

def norm_label(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())

def sanitize_filename(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", s).strip("_")

def sanitize_dirname(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._ -]+", "_", s).strip().strip("_")

def key_for_app(app_key: str) -> str:
    return f"{app_key}_topics"

def derive_title_from_permalink(permalink: str) -> str:
    parts = permalink.split("/")
    if "comments" in parts:
        i = parts.index("comments")
        if len(parts) > i + 2:
            return parts[i + 2].replace("-", " ").replace("_", " ").strip() or "Untitled"
    return "Untitled"

APP_INFO = {
    # Productivity App
    norm_app("Google Drive"):                 {"category": "Productivity", "sub": "googleworkspace"},
    norm_app("Google Docs"):                  {"category": "Productivity", "sub": "googledocs"},
    norm_app("CAmScanner"):                   {"category": "Productivity", "search": "CamScanner"},
    norm_app("Google Gemini"):                {"category": "Productivity", "sub": "GoogleGeminiAI"},
    norm_app("Google Sheets"):                {"category": "Productivity", "sub": "googlesheets"},
    norm_app("Microsoft Word: Edit Documents"): {"category": "Productivity", "sub": "MicrosoftWord"},
    norm_app("ChatGPT"):                      {"category": "Productivity", "sub": "ChatGPT"},
    norm_app("Perplexity"):                   {"category": "Productivity", "sub": "perplexity_ai"},
    norm_app("Adobe Acrobat Reader"):         {"category": "Productivity", "sub": "Acrobat"},

    # Social networking (Pinterest default lives under Share photos & videos)
    norm_app("Facebook"):                     {"category": "Social networking", "sub": "facebook"},
    norm_app("Pinterest"):                    {"category": "Share photos & videos", "sub": "Pinterest"},
    norm_app("Reddit"):                       {"category": "Social networking", "sub": "reddit"},
    norm_app("SnapChat"):                     {"category": "Social networking", "sub": "snapchat"},
    norm_app("telegram"):                     {"category": "Social networking", "sub": "Telegram"},
    norm_app("Signal"):                       {"category": "Social networking", "sub": "signal"},
    norm_app("Ok: Social network"):           {"category": "Social networking", "sub": "okru"},

    # Communication
    norm_app("Zoom"):                         {"category": "Communication", "sub": "Zoom"},
    norm_app("Discord"):                      {"category": "Communication", "sub": "discordapp"},
    norm_app("imo"):                          {"category": "Communication", "search": "imo app"},
    norm_app("Viber"):                        {"category": "Communication", "sub": "viber"},
    norm_app("WhatsApp"):                     {"category": "Communication", "sub": "WhatsApp"},
    norm_app("Facebook Messenger"):           {"category": "Communication", "sub": "FacebookMessenger"},
    norm_app("Google Meet"):                  {"category": "Communication", "sub": "GoogleMeet"},
    norm_app("Ms Teams"):                     {"category": "Communication", "sub": "MicrosoftTeams"},

    # Share photos & videos
    norm_app("TickTock Live"):                {"category": "Share photos & videos", "sub": "TikTok"},
    norm_app("TikTok Studio"):                {"category": "Share photos & videos", "sub": "TikTokhelp"},
    norm_app("Bigo Live"):                    {"category": "Share photos & videos", "sub": "BIGOLIVE"},
    norm_app("Moj: short Drame and Reels"):   {"category": "Share photos & videos", "search": "Moj app"},
    norm_app("Likee"):                        {"category": "Share photos & videos", "sub": "Likee"},
    norm_app("Twitch"):                       {"category": "Share photos & videos", "sub": "Twitch"},
    norm_app("Threads"):                      {"category": "Share photos & videos", "sub": "ThreadsApp"},

    # Travel & local
    norm_app("Uber"):                         {"category": "Travel & local", "sub": "uber"},
    norm_app("Rapido"):                       {"category": "Travel & local", "search": "Rapido app"},
    norm_app("Booking.com"):                  {"category": "Travel & local", "sub": "Bookingcom"},
    norm_app("Airbnd"):                       {"category": "Travel & local", "sub": "AirBnB"},
    norm_app("InDrive"):                      {"category": "Travel & local", "sub": "Indrive"},
    norm_app("ConfirmTKt"):                   {"category": "Travel & local", "search": "ConfirmTkt"},
    norm_app("train booking ap"):             {"category": "Travel & local", "sub": "IRCTC"},
    norm_app("redBus book Bus"):              {"category": "Travel & local", "sub": "redbus"},
}

CATEGORY_LISTS = {
    "Productivity": [
        "Google Drive","Google Docs","CAmScanner","Google Gemini","Google Sheets",
        "Microsoft Word: Edit Documents","ChatGPT","Perplexity","Adobe Acrobat Reader",
    ],
    "Social networking": [
        "Facebook","Pinterest","Reddit","SnapChat","telegram","Signal","Ok: Social network",
    ],
    "Communication": [
        "Zoom","Discord","imo","Viber","WhatsApp","Facebook Messenger","Google Meet","Ms Teams",
    ],
    "Share photos & videos": [
        "Pinterest","TickTock Live","TikTok Studio","Bigo Live",
        "Moj: short Drame and Reels","Likee","Twitch","Threads",
    ],
    "Travel & local": [
        "Uber","Rapido","Booking.com","Airbnd","InDrive","ConfirmTKt","train booking ap","redBus book Bus",
    ],
}
VALID_CATEGORIES = list(CATEGORY_LISTS.keys())
CATEGORY_NORM_TO_CANON = {norm_label(c): c for c in VALID_CATEGORIES}
CATEGORY_ALIASES = {
    "social": "Social networking",
    "socialnetworking": "Social networking",
    "sharephotosvideos": "Share photos & videos",
    "sharephotosandvideos": "Share photos & videos",
    "travellocal": "Travel & local",
    "travelandlocal": "Travel & local",
    "communication": "Communication",
    "productivity": "Productivity",
    "all": "*",
    "*": "*",
}


def fetch_subreddit_posts(subreddit_slug: str, max_posts: int, delay_seconds: float) -> list[dict]:
    headers = {"User-Agent": UA_BROWSER, "Accept": "application/json"}
    base_url = f"https://www.reddit.com/r/{subreddit_slug}/.json"
    posts, after = [], None
    while len(posts) < max_posts:
        limit = min(MAX_REDDIT_PAGE_SIZE, max_posts - len(posts))
        params = {"limit": limit}
        if after: params["after"] = after
        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.get(base_url, headers=headers, params=params, timeout=15)
                if resp.status_code == 429 or 500 <= resp.status_code < 600:
                    wait = delay_seconds * (attempt + 1)
                    print(f"Transient HTTP {resp.status_code} on r/{subreddit_slug}; sleeping {wait:.1f}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                break
            except RequestException as e:
                if attempt == MAX_RETRIES - 1:
                    raise RuntimeError(f"Request failed scraping r/{subreddit_slug}: {e}") from e
                wait = delay_seconds * (attempt + 1)
                print(f"Request error on r/{subreddit_slug}; sleeping {wait:.1f}s...")
                time.sleep(wait)
        else:
            raise RuntimeError(f"Failed after {MAX_RETRIES} retries scraping r/{subreddit_slug}")
        payload = resp.json()
        children = payload.get("data", {}).get("children", [])
        if not children: break
        for child in children:
            d = child.get("data") or {}
            permalink = urljoin("https://www.reddit.com", d.get("permalink", ""))
            title = d.get("title") or derive_title_from_permalink(permalink)
            posts.append({
                "title": title, "url": permalink, "score": d.get("score"),
                "num_comments": d.get("num_comments"), "created_utc": d.get("created_utc"),
                "author": d.get("author"), "subreddit": d.get("subreddit", subreddit_slug),
                "subreddit_name_prefixed": d.get("subreddit_name_prefixed", f"r/{subreddit_slug}"),
                "id": d.get("id"),
            })
            if len(posts) >= max_posts: break
        after = payload.get("data", {}).get("after")
        if not after: break
        time.sleep(delay_seconds)
    return posts

def fetch_search_posts(query: str, max_posts: int, delay_seconds: float) -> list[dict]:
    headers = {"User-Agent": UA_BROWSER, "Accept": "application/json"}
    base_url = "https://www.reddit.com/search.json"
    posts, after = [], None
    while len(posts) < max_posts:
        limit = min(MAX_REDDIT_PAGE_SIZE, max_posts - len(posts))
        params = {"q": query, "limit": limit}
        if after: params["after"] = after
        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.get(base_url, headers=headers, params=params, timeout=15)
                if resp.status_code == 429 or 500 <= resp.status_code < 600:
                    wait = delay_seconds * (attempt + 1)
                    print(f"Transient HTTP {resp.status_code} on search '{query}'; sleeping {wait:.1f}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                break
            except RequestException as e:
                if attempt == MAX_RETRIES - 1:
                    raise RuntimeError(f"Request failed searching '{query}': {e}") from e
                wait = delay_seconds * (attempt + 1)
                print(f"Request error on search '{query}'; sleeping {wait:.1f}s...")
                time.sleep(wait)
        else:
            raise RuntimeError(f"Failed after {MAX_RETRIES} retries searching '{query}'")
        payload = resp.json()
        children = payload.get("data", {}).get("children", [])
        if not children: break
        for child in children:
            d = child.get("data") or {}
            permalink = urljoin("https://www.reddit.com", d.get("permalink", ""))
            title = d.get("title") or derive_title_from_permalink(permalink)
            posts.append({
                "title": title, "url": permalink, "score": d.get("score"),
                "num_comments": d.get("num_comments"), "created_utc": d.get("created_utc"),
                "author": d.get("author"), "subreddit": d.get("subreddit"),
                "subreddit_name_prefixed": d.get("subreddit_name_prefixed"), "id": d.get("id"),
            })
            if len(posts) >= max_posts: break
        after = payload.get("data", {}).get("after")
        if not after: break
        time.sleep(delay_seconds)
    return posts


def scrape_one_target(app_key: str, info: dict, max_posts: int, delay_seconds: float) -> dict:
    if "sub" in info:
        slug = info["sub"]
        print(f"Scraping r/{slug} (up to {max_posts} posts)...")
        posts = fetch_subreddit_posts(slug, max_posts, delay_seconds)
        display_name = posts[0].get("subreddit", slug) if posts else slug
        title = posts[0].get("subreddit_name_prefixed", f"r/{slug}") if posts else f"r/{slug}"
        source_url = f"https://www.reddit.com/r/{slug}/"
        mode, source = "subreddit", slug
    else:
        query = info["search"]
        print(f"Searching Reddit for '{query}' (up to {max_posts} posts)...")
        posts = fetch_search_posts(query, max_posts, delay_seconds)
        display_name = f"Search: {query}"
        title = f"Search: {query}"
        source_url = f"https://www.reddit.com/search/?q={requests.utils.quote(query)}"
        mode, source = "search", query

    data = {
        "app_key": app_key,
        "category": info.get("category", "Uncategorized"),
        "mode": mode,
        "source": source,
        "url": source_url,
        "title": title,
        "subreddit": display_name,
        "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_posts_collected": len(posts),
    }

    topics_key = key_for_app(app_key)
    topics, discussions, seen = [], [], set()
    for post in posts:
        permalink = post.get("url", "")
        if not permalink or permalink in seen: continue
        seen.add(permalink)
        ptitle = (post.get("title") or "Untitled").strip() or "Untitled"
        discussions.append({
            "title": ptitle, "url": permalink, "type": "discussion",
            "score": post.get("score"), "num_comments": post.get("num_comments"),
            "created_utc": post.get("created_utc"), "author": post.get("author"),
            "post_subreddit": post.get("subreddit"),
        })
        topics.append({
            "title": ptitle, "type": f"{app_key}_topic", "post_url": permalink,
            "score": post.get("score"), "num_comments": post.get("num_comments"),
            "created_utc": post.get("created_utc"), "post_subreddit": post.get("subreddit"),
        })
    data[topics_key] = topics
    data["discussions"] = discussions
    data["posts"] = posts
    return data

def canonical_category(label: str) -> str | list[str] | None:
    nk = norm_label(label)
    if nk in CATEGORY_NORM_TO_CANON: return CATEGORY_NORM_TO_CANON[nk]
    if nk in CATEGORY_ALIASES:
        canon = CATEGORY_ALIASES[nk]
        return VALID_CATEGORIES if canon == "*" else canon
    return None

def build_targets_from_categories(categories: list[str]) -> list[tuple[str, dict]]:
    # Expand categories (aliases + '*' support)
    expanded = []
    for c in categories:
        canon = canonical_category(c)
        if canon is None:
            print(f"Unknown category '{c}'")
            continue
        if isinstance(canon, list):  # '*' expanded
            expanded.extend(canon)
        else:
            expanded.append(canon)

    targets, seen = [], set()
    for cat in expanded:
        app_names = CATEGORY_LISTS.get(cat, [])
        for display in app_names:
            app_key = norm_app(display)
            base_info = APP_INFO.get(app_key)
            if not base_info:
                print(f"Skipping unknown app '{display}' in category '{cat}'")
                continue
            info = dict(base_info)
            info["category"] = cat  # override to requested cat
            sig = (app_key, cat)
            if sig not in seen:
                targets.append((app_key, info))
                seen.add(sig)
    return targets

def build_targets_from_apps(apps: list[str]) -> list[tuple[str, dict]]:
    targets, seen = [], set()
    for name in apps:
        key = norm_app(name)
        if key in APP_INFO:
            info = APP_INFO[key]
            sig = (key, info.get("category",""))
            if sig not in seen:
                targets.append((key, info))
                seen.add(sig)
        else:
            print(f"Skipping unknown app '{name}' (normalized '{key}')")
    return targets

def scrape_reddit(selected_apps: list[str], selected_categories: list[str], max_posts: int, delay_seconds: float) -> list[dict]:
    targets = []
    if selected_categories:
        targets.extend(build_targets_from_categories(selected_categories))
    if selected_apps:
        targets.extend(build_targets_from_apps(selected_apps))
    if not selected_apps and not selected_categories:
        targets = [(k, v) for k, v in APP_INFO.items()]
        targets.sort(key=lambda kv: (kv[1].get("category",""), kv[0]))
    if not targets:
        print("No valid targets.")
        return []

    deduped, seen = [], set()
    for app_key, info in targets:
        # Deduplicate per source so apps listed in multiple categories are scraped only once.
        sig = (app_key, info.get("sub"), info.get("search"))
        if sig in seen: continue
        seen.add(sig); deduped.append((app_key, info))

    results = []
    for app_key, info in deduped:
        try:
            result = scrape_one_target(app_key, info, max_posts, delay_seconds)
            results.append(result)
            topics_key = key_for_app(app_key)
            topics_count = len(result.get(topics_key, []))
            discussions_count = len(result.get("discussions", []))
            posts_count = result.get("total_posts_collected", 0)
            print(
                f"Collected for {app_key}: "
                f"{posts_count} posts, {topics_count} topics, {discussions_count} discussions"
            )
        except Exception as e:
            print(f"ERROR ({app_key}): {e}")
        time.sleep(delay_seconds)
    return results


def save_scraped_data_per_app(data: list[dict], outdir: str) -> None:
    if not data:
        print("No data"); return
    for sub in data:
        category_label = sub.get("category", "Uncategorized")
        app_key = sub.get("app_key", "unknown")
        cat_dir = os.path.join(outdir, sanitize_dirname(category_label))
        os.makedirs(cat_dir, exist_ok=True)
        base = sanitize_filename(app_key)
        json_name = os.path.join(cat_dir, f"{base}_topics.json")
        csv_name = os.path.join(cat_dir, f"{base}_topics.csv")

        try:
            with open(json_name, "w", encoding="utf-8") as f:
                json.dump(sub, f, indent=2, ensure_ascii=True)
            print(f"Saved JSON -> {json_name}")
        except Exception as e:
            print("ERROR (JSON):", e)

        try:
            with open(csv_name, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["App Key","Category","Type","Title","URL","Post Subreddit","Scraped At"])
                scraped_at = sub.get("scraped_at", "")
                category = sub.get("category", "")
                app = sub.get("app_key", "")
                for k, v in sub.items():
                    if k.endswith("_topics") and isinstance(v, list):
                        for topic in v:
                            w.writerow([
                                app, category, topic.get("type",""),
                                topic.get("title",""), topic.get("post_url",""),
                                topic.get("post_subreddit",""), scraped_at,
                            ])
                for d in sub.get("discussions", []):
                    w.writerow([
                        app, category, d.get("type",""),
                        d.get("title",""), d.get("url",""),
                        d.get("post_subreddit",""), scraped_at,
                    ])
            print(f"Saved CSV  -> {csv_name}")
        except Exception as e:
            print("ERROR (CSV):", e)


def _flatten_commas(seq):
    """Only split on commas; keep spaces/& intact (fix for quoted categories)."""
    out = []
    if not seq: return out
    for item in seq:
        out.extend([p.strip() for p in item.split(",") if p.strip()])
    return out

def main() -> None:
    parser = argparse.ArgumentParser(description="Reddit scraper for multiple apps (by category).")
    parser.add_argument("-a","--app", nargs="+",
                        help="Apps to scrape. You can repeat -a or separate with commas.")
    parser.add_argument("-c","--categories", nargs="+",
                        help="Categories to scrape. Use quotes for names with spaces/&, or use aliases (e.g., sharephotosvideos).")
    parser.add_argument("--list-categories", action="store_true", help="List available categories and exit")
    parser.add_argument("--max-posts", type=int, default=DEFAULT_MAX_POSTS,
                        help="Max posts per source (default: %(default)s)")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY_SECONDS,
                        help="Delay between requests (seconds) (default: %(default)s)")
    parser.add_argument("--outdir", type=str, default=DEFAULT_OUTDIR,
                        help="Root output directory (default: %(default)s)")
    args = parser.parse_args()

    if args.list_categories:
        print("Available categories:")
        for c in VALID_CATEGORIES:
            print(f" - {c}")
        print("\nAliases: social | socialnetworking | sharephotosvideos | sharephotosandvideos | "
              "travellocal | travelandlocal | communication | productivity | all")
        return

    selected_apps = _flatten_commas(args.app)
    selected_categories = _flatten_commas(args.categories)

    if args.max_posts <= 0:
        parser.error("--max-posts must be a positive integer")
    if args.delay < 0:
        parser.error("--delay cannot be negative")

    data = scrape_reddit(selected_apps, selected_categories, args.max_posts, args.delay)

    if data:
        total_topics = 0
        total_discussions = 0
        for sub in data:
            topic_lists = [v for k, v in sub.items() if k.endswith("_topics") and isinstance(v, list)]
            total_topics += sum(len(lst) for lst in topic_lists)
            total_discussions += len(sub.get("discussions", []))
        print(f"\nTotal: {total_topics} Topics, {total_discussions} Discussions")
        save_scraped_data_per_app(data, args.outdir)
    else:
        print("There is no data returned!")

if __name__ == "__main__":
    main()
