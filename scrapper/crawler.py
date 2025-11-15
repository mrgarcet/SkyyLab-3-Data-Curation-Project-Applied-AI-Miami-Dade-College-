"""
crawler.py (v3)

This file is the missing crawler/scraper that was not included
with the original MDC scraping utilities.

Goal:
- Start from https://www.mdc.edu/
- Crawl internal MDC pages (within mdc.edu)
- Respect basic robots.txt rules (for User-agent: *)
- Avoid obvious non-HTML resources (PDFs, images, docs)
- Produce a text file with one URL per line for later cleaning/scraping
"""

import time
import datetime
from typing import List
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

# -----------------------------
# CONFIG / CONSTANTS
# -----------------------------

# Where to start the crawl from (we can add more later if needed)
SEED_URLS: List[str] = ["https://www.mdc.edu/"]

# Safety limit so the crawler does not run forever
# v2 ran out limit of 10000 and v2 data document where created
# v3 adjusted to 20000 but was not executed due to time constrain of project.
DEFAULT_MAX_PAGES: int = 20000

# Network settings
REQUEST_TIMEOUT: int = 20      # seconds to wait for each HTTP response
REQUEST_DELAY: float = 1.0     # seconds to sleep between requests (politeness)

# Only stay within this domain
ALLOWED_DOMAIN_SUFFIX: str = "mdc.edu"

# Paths that robots.txt says are disallowed for all user-agents
# User-agent: *
# Disallow: /newsandnotes/
# Disallow: /trackback/
# Disallow: /publications/
# Disallow: /email/
DISALLOWED_PATH_PREFIXES = (
    "/newsandnotes/",
    "/trackback/",
    "/publications/",
    "/email/",
)

# File extensions we don't want to crawl (non-HTML, large files, etc.)
"""" 
v3 removed .pdf extension exception, pdf information found to be useful and important
pdf links will be scrapped and added into it own data .txt file.
"""
SKIP_EXTENSIONS = (
    #".pdf",
    ".jpg", ".jpeg", ".png", ".gif",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".rar", ".mp4", ".mp3",
)

# Output files
# Updated to v3 already
# UPDATE VERSION NUMBER IF ADJUSTING CODE FOR CRAWLER - remember to update link_cleaner path
OUTPUT_LINKS_PATH: str = "../data/mdc_links_raw_v3.txt"     # UPDATE VERSION NUMBER BEFORE RUNNING
ERROR_LOG_PATH: str = "../data/mdc_crawler_errors_v3.log"   # UPDATE VERSION NUMBER BEFORE RUNNING

# Optional custom User-Agent (just to be polite/clear)
HEADERS = {
    "User-Agent": "MDC-Student-Crawler/1.0 (for AI class project)"
}


# -----------------------------
# HELPER FUNCTIONS
# -----------------------------

def normalize_url(url: str) -> str:
    """
    Normalize URLs for de-duplication:
    - Strip off any fragment (#something)
    - Optionally, we could add more rules later (trailing slashes, etc.)
    """
    clean_url, _ = urldefrag(url)  # removes #fragment
    return clean_url


def is_disallowed_path(path: str) -> bool:
    """
    Return True if the path is disallowed by robots.txt rules for User-agent: *
    (we hard-code the known disallowed prefixes here).
    """
    for prefix in DISALLOWED_PATH_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def has_skipped_extension(path: str) -> bool:
    """
    Return True if the URL path clearly points to a resource we don't want
    (PDFs, images, documents, etc.).
    """
    lower = path.lower()
    return lower.endswith(SKIP_EXTENSIONS)

## (v2) add below helper to ignore confirmation or login links
def should_skip_url(url: str) -> bool:
    """
    Return True for URLs we know are pointless to crawl:
    - calendar event confirmation links
    - generic auth / shibboleth login endpoints
    You can add more patterns here as you discover them.
    """
    if "calendar.mdc.edu/event/" in url and "confirm" in url:
        return True
    if "auth/shib_login" in url:
        return True
    # add any other patterns you know are always forbidden
    return False



def log_error(message: str) -> None:
    """
    Append an error message with timestamp to the error log file.
    """
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    line = f"[{timestamp}] {message}\n"
    with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line)


# -----------------------------
# MAIN CRAWL FUNCTION
# -----------------------------

def crawl_mdc(seed_urls: List[str], max_pages: int = DEFAULT_MAX_PAGES) -> List[str]:
    """
    Crawl MDC starting from the given seed URLs.

    - Only follows links within the mdc.edu domain.
    - Skips disallowed paths and undesired file types.
    - Returns a list of successfully fetched page URLs.
    """
    start_time = time.time()


    seen = set()          # URLs we have already processed
    to_visit = list(seed_urls)  # Frontier of URLs to crawl
    results: List[str] = []

    while to_visit and len(results) < max_pages:
        url = to_visit.pop(0)
        url = normalize_url(url)

        # Skip known pointless URLs (logins, confirm links, etc.)
        if should_skip_url(url):
            continue

        # Skip URLs we've already seen
        if url in seen:
            continue
        seen.add(url)

        # Parse URL for domain/path checks
        parsed = urlparse(url)
        if not parsed.scheme.startswith("http"):
            # Skip mailto:, javascript:, etc.
            continue

        if not parsed.netloc.endswith(ALLOWED_DOMAIN_SUFFIX):
            # Stay within mdc.edu
            continue

        if is_disallowed_path(parsed.path):
            # Respect robots.txt disallow rules (for User-agent: *)
            continue

        if has_skipped_extension(parsed.path):
            # Skip obviously non-HTML resources (PDFs, images, docs, etc.)
            continue

        # Fetch the page
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS)
        except Exception as e:
            log_error(f"REQUEST ERROR for {url}: {repr(e)}")
            continue

        if resp.status_code != 200:
            log_error(f"HTTP {resp.status_code} for {url}")
            continue

        # We got a good HTML page
        results.append(url)
        elapsed = time.time() - start_time
        print(f"[{len(results)}] {url} - elapsed: {elapsed:.1f}s, frontier={len(to_visit)}")

        # If this is a PDF, don't try to parse it as HTML or discover links from it
        if parsed.path.lower().endswith(".pdf"):
            time.sleep(REQUEST_DELAY)
            continue

        # Parse HTML and discover new links
        soup = BeautifulSoup(resp.text, "html.parser")


        for a in soup.find_all("a", href=True):
            href = a["href"]
            full = urljoin(url, href)  # make relative links absolute
            full = normalize_url(full) # remove #fragment

            # We'll let the top of the loop handle domain/extension checks
            if full not in seen:
                to_visit.append(full)

        # Be polite: pause between requests
        time.sleep(REQUEST_DELAY)

    return results


# -----------------------------
# SCRIPT ENTRY POINT
# -----------------------------

if __name__ == "__main__":
    print("Starting MDC crawl...")
    crawled_urls = crawl_mdc(SEED_URLS, max_pages=DEFAULT_MAX_PAGES)

    # REPORT WHY WE STOPPED
    if len(crawled_urls) >= DEFAULT_MAX_PAGES:
        print(f"\nSTOPPED because max_pages ({DEFAULT_MAX_PAGES}) was reached.")
    else:
        print("\nDONE: Reached the TRUE end of the website (no more pages to crawl).")

    # Save results (v2 output paths)
    with open(OUTPUT_LINKS_PATH, "w", encoding="utf-8") as f:
        for url in crawled_urls:
            f.write(url + "\n")

    print(f"\nSaved {len(crawled_urls)} URLs to {OUTPUT_LINKS_PATH}")
    print(f"Errors (if any) are logged in {ERROR_LOG_PATH}")

