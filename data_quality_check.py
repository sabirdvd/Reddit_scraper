import argparse
import glob
import json
import os


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate scraped Reddit JSON output quality.")
    parser.add_argument(
        "--outdir",
        default="output",
        help="Root output directory that contains per-category JSON files (default: %(default)s)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero status if any file has shape issues or duplicate URLs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pattern = os.path.join(args.outdir, "**", "*_topics.json")
    files = sorted(glob.glob(pattern, recursive=True))

    if not files:
        print(f"No JSON files found under '{args.outdir}'")
        return 1

    total_posts = 0
    global_urls = []
    files_with_shape_issue = 0
    files_with_dup_urls = 0

    print("Per-file quality report:")
    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)

        app = data.get("app_key", "unknown")
        posts = data.get("posts", [])
        discussions = data.get("discussions", [])
        topic_lists = [v for k, v in data.items() if k.endswith("_topics") and isinstance(v, list)]
        topics = topic_lists[0] if topic_lists else []

        urls = [p.get("url") for p in posts if p.get("url")]
        dup_in_file = len(urls) - len(set(urls))
        empty_titles = sum(1 for p in posts if not (p.get("title") or "").strip())
        missing_authors = sum(1 for p in posts if not p.get("author"))
        shape_ok = len(posts) == len(topics) == len(discussions)

        if not shape_ok:
            files_with_shape_issue += 1
        if dup_in_file > 0:
            files_with_dup_urls += 1

        total_posts += len(posts)
        global_urls.extend(urls)

        print(
            f"- {app:30} posts={len(posts):4} dup_urls={dup_in_file:3} "
            f"empty_titles={empty_titles:3} missing_authors={missing_authors:3} shape_ok={shape_ok}"
        )

    global_dup_urls = len(global_urls) - len(set(global_urls))
    print("\nSummary:")
    print(f"- files: {len(files)}")
    print(f"- total_posts: {total_posts}")
    print(f"- global_duplicate_urls: {global_dup_urls}")
    print(f"- files_with_shape_issue: {files_with_shape_issue}")
    print(f"- files_with_dup_urls: {files_with_dup_urls}")

    if args.strict and (files_with_shape_issue > 0 or files_with_dup_urls > 0):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
