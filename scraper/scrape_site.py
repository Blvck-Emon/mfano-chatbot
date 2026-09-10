"""
scrape_site.py
================
Task-2/3 tool (Information Source Identification & Collection).

Crawls the entire Mfano Bora Africa website (same-domain, breadth-first),
extracts readable body text from each page, splits it into
retrieval-sized chunks, and writes everything to a CSV that
`csv-loader/load_csv_to_mysql.py` loads straight into the
`knowledge_base` MySQL table.

Design goals (kept deliberately lightweight, no headless browser):
  * requests + BeautifulSoup only -> works on a cheap shared host / cron job
  * respects robots.txt (via urllib.robotparser)
  * de-dupes pages and text chunks
  * stays on-domain, ignores files (pdf/jpg/etc.), mailto:, tel:, #anchors
  * polite crawl delay + custom User-Agent
  * idempotent: re-running overwrites the CSV with a fresh crawl

Usage:
    python scrape_site.py --base-url https://www.mfanoboraafrica.com \
                           --out ../database/knowledge_base_scraped.csv \
                           --max-pages 200 --delay 1.0

The resulting CSV columns match `database/schema.sql`'s `knowledge_base`
table so it can be loaded as-is:
    category,question,content_chunk,keywords,source_url,source_type
"""

import argparse
import csv
import re
import sys
import time
from collections import deque
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

DEFAULT_HEADERS = {
    "User-Agent": "MfanoBoraChatbotKB/1.0 (+info@mfanoboraafrica.com; internal KB indexer)"
}

# Very small keyword->category map used to auto-tag scraped chunks.
# Extend this as the site's real information architecture is confirmed
# (Task 4: Information Classification).
CATEGORY_RULES = [
    ("Careers & Attachments", ("attachment", "internship", "career", "apply", "mentoring")),
    ("Awards & Achievements", ("award", "gala", "transport awards", "recognition")),
    ("Road Safety Club", ("road safety club", "road safety", "school campaign")),
    ("Services", ("logistics", "supply chain", "consultancy", "consulting")),
    ("Company & Contact", ("contact", "location", "hours", "about us", "office")),
    ("Blog & News", ("blog", "news", "article", "press")),
]

# Text nodes shorter than this are dropped as noise (menu items, etc.)
MIN_CHUNK_CHARS = 60
# Target size for a retrieval chunk (roughly 2-4 sentences).
CHUNK_TARGET_CHARS = 700

SKIP_EXTENSIONS = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".zip",
    ".doc", ".docx", ".xls", ".xlsx", ".css", ".js", ".ico", ".mp4",
)


def is_same_domain(url: str, domain: str) -> bool:
    return urlparse(url).netloc.replace("www.", "") == domain.replace("www.", "")


def normalize_url(url: str) -> str:
    """Strip fragments/query noise so we don't crawl the same page twice."""
    parsed = urlparse(url)
    return parsed._replace(fragment="", query="").geturl().rstrip("/")


def load_robots(base_url: str) -> RobotFileParser:
    rp = RobotFileParser()
    rp.set_url(urljoin(base_url, "/robots.txt"))
    try:
        rp.read()
    except Exception:
        # If robots.txt is unreachable, fail safe: allow crawl but stay polite.
        pass
    return rp


def guess_category(text: str) -> str:
    lower = text.lower()
    for category, keywords in CATEGORY_RULES:
        if any(k in lower for k in keywords):
            return category
    return "General FAQ"


def extract_chunks(html: str, url: str):
    """Pull clean body text out of a page and split into retrieval chunks."""
    soup = BeautifulSoup(html, "html.parser")

    # Drop non-content elements.
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "form"]):
        tag.decompose()

    title = soup.title.get_text(strip=True) if soup.title else ""

    # Prefer <main>/<article> if present, else fall back to <body>.
    container = soup.find("main") or soup.find("article") or soup.body or soup
    blocks = container.find_all(["p", "li", "h1", "h2", "h3"])

    raw_text = "\n".join(
        b.get_text(" ", strip=True) for b in blocks if b.get_text(strip=True)
    )
    raw_text = re.sub(r"\s+", " ", raw_text).strip()

    if len(raw_text) < MIN_CHUNK_CHARS:
        return []

    # Greedy chunking on sentence boundaries.
    sentences = re.split(r"(?<=[.!?])\s+", raw_text)
    chunks, current = [], ""
    for sentence in sentences:
        if len(current) + len(sentence) > CHUNK_TARGET_CHARS and current:
            chunks.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current.strip())

    results = []
    for chunk in chunks:
        if len(chunk) < MIN_CHUNK_CHARS:
            continue
        results.append({
            "category": guess_category(f"{title} {chunk}"),
            "question": "",  # left blank for scraped content; FAQ rows fill this in
            "content_chunk": chunk,
            "keywords": title,
            "source_url": url,
            "source_type": "scraped",
        })
    return results


def find_links(html: str, current_url: str, base_url: str, domain: str):
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        full = normalize_url(urljoin(current_url, href))
        if not is_same_domain(full, domain):
            continue
        if full.lower().endswith(SKIP_EXTENSIONS):
            continue
        links.add(full)
    return links


def crawl(base_url: str, max_pages: int, delay: float):
    domain = urlparse(base_url).netloc
    robots = load_robots(base_url)

    start = normalize_url(base_url)
    visited = set()
    queue = deque([start])
    all_rows = []

    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    while queue and len(visited) < max_pages:
        url = queue.popleft()
        if url in visited:
            continue
        if not robots.can_fetch(DEFAULT_HEADERS["User-Agent"], url):
            print(f"[skip:robots] {url}")
            continue

        try:
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                visited.add(url)
                continue
        except requests.RequestException as exc:
            print(f"[error] {url} -> {exc}")
            visited.add(url)
            continue

        visited.add(url)
        print(f"[{len(visited)}/{max_pages}] scraped {url}")

        rows = extract_chunks(resp.text, url)
        all_rows.extend(rows)

        for link in find_links(resp.text, url, base_url, domain):
            if link not in visited:
                queue.append(link)

        time.sleep(delay)

    return all_rows


def write_csv(rows, out_path: str):
    fieldnames = ["category", "question", "content_chunk", "keywords", "source_url", "source_type"]
    seen_text = set()
    deduped = []
    for row in rows:
        key = row["content_chunk"][:120]
        if key in seen_text:
            continue
        seen_text.add(key)
        deduped.append(row)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(deduped)

    print(f"\nWrote {len(deduped)} unique chunks to {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Scrape mfanoboraafrica.com into a KB CSV")
    parser.add_argument("--base-url", default="https://www.mfanoboraafrica.com")
    parser.add_argument("--out", default="../database/knowledge_base_scraped.csv")
    parser.add_argument("--max-pages", type=int, default=200)
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between requests (politeness)")
    args = parser.parse_args()

    print(f"Starting crawl of {args.base_url} (max {args.max_pages} pages, {args.delay}s delay)")
    rows = crawl(args.base_url, args.max_pages, args.delay)
    if not rows:
        print("No content extracted. Check the base URL or site availability.", file=sys.stderr)
        sys.exit(1)
    write_csv(rows, args.out)


if __name__ == "__main__":
    main()
