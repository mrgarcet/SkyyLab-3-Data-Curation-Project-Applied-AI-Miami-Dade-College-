#!/usr/bin/env python3
"""
page_scraper.py (v1.0.0)

MVP HTML scraper for the MDC project (Skyy).
- Reads target URLs (HTML only; MVP categories).
- Fetches with polite delay + retries.
- Extracts: title, meta description, canonical URL, h1/h2/h3, cleaned text,
  contact facts (emails/phones/$/dates), language, robots/generator meta,
  OpenGraph/Twitter meta, breadcrumbs, JSON-LD types, CTA anchors, link summaries.
- Joins in category metadata from urls_with_category_v3.csv.
- Writes line-delimited JSON to ../data/mdc_pages_v3.jsonl.
- Resume-friendly: skips URLs already present in output.

Run:
  python scraper/page_scraper.py \
    --in_urls ../data/target_links_v3.txt \
    --in_labels ../data/urls_with_category_v3.csv \
    --out_jsonl ../data/mdc_pages_v3.jsonl
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import time
import os
import datetime as dt
from typing import Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urlparse, urljoin, urlunparse

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

# ---------- CLI defaults ----------
DEFAULT_IN_URLS   = "../data/target_links_v3.txt"
DEFAULT_IN_LABELS = "../data/urls_with_category_v3.csv"
DEFAULT_OUT_JSONL = "../data/mdc_pages_v3.jsonl"

USER_AGENT = "SkyyScraper/1.0  contact: lorenzo.garcet001@mymdc.net"

# Skip anything that looks like authentication, PeopleSoft frames, etc.
SKIP_PATTERNS = [
    r"\b/psp/\b", r"\b/psc/\b", r"\bNUI_FRAMEWORK\b",
    r"/(Account|Login|SignIn|Sign-In|Sign_In)/?",
    r"^https?://(my|login|idp|auth|sso|cas)\.mdc\.edu",
    r"\b/portal\b", r"\b/selfservice\b", r"\b/peopletools\b",
]

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

REQUEST_TIMEOUT = 25
RETRY_COUNT = 2
DELAY_MIN = 0.5
DELAY_MAX = 1.0

# --------- Helpers ---------
def utc_now_z() -> str:
    """Return UTC timestamp like 2025-11-17T14:05:23Z (Python 3.12-safe)."""
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")

def norm_url(u: str) -> str:
    return u.strip()

def is_skipped(url: str) -> bool:
    return any(re.search(p, url, flags=re.IGNORECASE) for p in SKIP_PATTERNS)

def is_html_content_type(ctype: Optional[str]) -> bool:
    if not ctype:
        return False
    return "text/html" in ctype.lower() or "application/xhtml+xml" in ctype.lower()

def load_url_list(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def load_labels(path: str) -> Dict[str, Dict[str, str]]:
    """Return {url: {'category':..., 'confidence':..., 'reason':...}}"""
    out: Dict[str, Dict[str, str]] = {}
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            u = row.get("url", "").strip()
            if not u:
                continue
            out[u] = {
                "category": row.get("category", "").strip(),
                "confidence": row.get("confidence", "").strip(),
                "reason": row.get("reason", "").strip(),
            }
    return out

def already_scraped(path: str) -> Set[str]:
    seen: Set[str] = set()
    if not os.path.exists(path):
        return seen
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                u = obj.get("url") or obj.get("meta", {}).get("url")
                if u:
                    seen.add(u)
            except Exception:
                continue
    return seen

def fetch(session: requests.Session, url: str) -> Tuple[int, str, str, str]:
    """
    Returns: (status_code, content_type, html_text, final_url)
    Raises on non-network exceptions after retries.
    """
    err: Optional[Exception] = None
    for attempt in range(RETRY_COUNT + 1):
        try:
            resp = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            status = resp.status_code
            ctype = resp.headers.get("Content-Type", "")
            final_url = str(resp.url)
            if 200 <= status < 300 and is_html_content_type(ctype):
                return status, ctype, resp.text, final_url
            else:
                # If not HTML, we still return the body (may be short) so caller can record/skips.
                return status, ctype, resp.text, final_url
        except Exception as e:
            err = e
            if attempt < RETRY_COUNT:
                time.sleep(0.6)
                continue
            break
    assert err is not None
    raise err

# --------- Extraction helpers ---------
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")
MONEY_RE = re.compile(r"\$\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?")
DATE_RE  = re.compile(r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|"
                      r"May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|"
                      r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:,\s*\d{4})?\b")

CTA_WORDS = re.compile(r"\b(apply|register|advis(e|ing|or)|testing|tuition|costs|financial aid|scholarship|contact|transcript|orientation)\b", re.I)

def text_from_node(node: Tag) -> str:
    parts: List[str] = []
    for element in node.descendants:
        if isinstance(element, NavigableString):
            txt = str(element).strip()
            if txt:
                parts.append(txt)
        elif isinstance(element, Tag) and element.name in {"script", "style", "noscript"}:
            # Skip embedded non-visible content
            continue
    return " ".join(parts)

def pick_main_node(soup: BeautifulSoup) -> Tag:
    # Prefer <main>; then obvious containers; else body.
    main = soup.find("main")
    if main:
        return main
    for sel in [
        {"id": "main"}, {"role": "main"},
        {"id": "content"}, {"class_": "content"},
        {"class_": "content-area"}, {"class_": "container"},
    ]:
        node = soup.find(True, **sel)  # any tag matching dict
        if node:
            return node
    return soup.body or soup

def clean_soup(soup: BeautifulSoup) -> None:
    # Drop global nav/footer/aside crumbs to reduce noise.
    for tag in soup.find_all(["nav", "footer", "aside"]):
        tag.decompose()
    # Remove obvious decorative or repeated UI
    for cls in ["breadcrumb", "breadcrumbs", "navbar", "nav", "menu", "sidebar", "pager",
                "cookie", "banner", "modal", "popup", "carousel", "slider"]:
        for t in soup.select(f".{cls}"):
            t.decompose()
    for name in ["script", "style", "noscript"]:
        for t in soup.find_all(name):
            t.decompose()

def get_title(soup: BeautifulSoup) -> Optional[str]:
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    ogt = soup.find("meta", property="og:title")
    if ogt and ogt.get("content"):
        return ogt["content"].strip()
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else None

def get_meta(soup: BeautifulSoup, name: str) -> Optional[str]:
    m = soup.find("meta", attrs={"name": name})
    return m.get("content", "").strip() if m and m.get("content") else None

def get_property(soup: BeautifulSoup, prop: str) -> Optional[str]:
    m = soup.find("meta", attrs={"property": prop})
    return m.get("content", "").strip() if m and m.get("content") else None

def get_canonical(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    link = soup.find("link", rel=lambda v: v and "canonical" in v.lower())
    if link and link.get("href"):
        return urljoin(base_url, link["href"])
    return None

def get_breadcrumbs(soup: BeautifulSoup) -> List[str]:
    crumbs: List[str] = []
    nav = soup.find("nav", attrs={"aria-label": re.compile("breadcrumb", re.I)}) \
          or soup.find("ol", class_=re.compile("breadcrumb", re.I))
    if nav:
        for a in nav.find_all("a"):
            txt = a.get_text(" ", strip=True)
            if txt:
                crumbs.append(txt)
    return crumbs

def extract_json_ld_types(soup: BeautifulSoup) -> List[str]:
    types: List[str] = []
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(s.get_text(strip=True))
            if isinstance(data, list):
                for item in data:
                    t = item.get("@type")
                    if isinstance(t, list):
                        types.extend([str(x) for x in t])
                    elif t:
                        types.append(str(t))
            elif isinstance(data, dict):
                t = data.get("@type")
                if isinstance(t, list):
                    types.extend([str(x) for x in t])
                elif t:
                    types.append(str(t))
        except Exception:
            continue
    # Deduplicate while keeping order
    seen: Set[str] = set()
    out: List[str] = []
    for t in types:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:10]

def extract_links(soup: BeautifulSoup, base_url: str) -> Dict[str, object]:
    internal: List[str] = []
    external: List[str] = []
    pdfs: List[str] = []
    mailtos: List[str] = []
    tels: List[str] = []
    ctas: List[str] = []

    base_host = urlparse(base_url).hostname or ""
    base_root = ".".join(base_host.split(".")[-2:]) if base_host else ""

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(" ", strip=True)[:120]
        if href.startswith("#"):
            continue
        if href.lower().startswith("mailto:"):
            mailtos.append(href)
        elif href.lower().startswith("tel:"):
            tels.append(href)
        else:
            absu = urljoin(base_url, href)
            p = urlparse(absu)
            host = p.hostname or ""
            if absu.lower().endswith(".pdf"):
                pdfs.append(absu)
            elif base_root and host.endswith(base_root):
                internal.append(absu)
            else:
                external.append(absu)
        # CTA detection
        if text and CTA_WORDS.search(text):
            ctas.append(text)

    # Dedup + small samples to keep JSON small
    def uniq(xs: List[str]) -> List[str]:
        s: Set[str] = set()
        out: List[str] = []
        for x in xs:
            if x not in s:
                s.add(x)
                out.append(x)
        return out

    internal = uniq(internal)
    external = uniq(external)
    pdfs = uniq(pdfs)
    mailtos = uniq(mailtos)
    tels = uniq(tels)
    ctas = uniq(ctas)

    return {
        "internal_count": len(internal),
        "external_count": len(external),
        "pdf_count": len(pdfs),
        "mailto_count": len(mailtos),
        "tel_count": len(tels),
        "internal_sample": internal[:20],
        "external_sample": external[:10],
        "pdf_sample": pdfs[:10],
        "mailto_sample": mailtos[:10],
        "tel_sample": tels[:10],
        "nav_ctas": ctas[:20],
    }

def parse_html(html: str, base_url: str) -> Dict[str, object]:
    soup = BeautifulSoup(html, "lxml")
    # Preserve <html lang>, robots/generator meta
    lang = None
    if soup.html and isinstance(soup.html, Tag):
        lang = soup.html.get("lang") or soup.html.get("xml:lang")

    meta_robots = get_meta(soup, "robots")
    meta_generator = get_meta(soup, "generator")

    # OpenGraph/Twitter
    og = {
        "title": get_property(soup, "og:title"),
        "description": get_property(soup, "og:description"),
        "type": get_property(soup, "og:type"),
        "url": get_property(soup, "og:url"),
    }
    twitter = {
        "title": get_meta(soup, "twitter:title"),
        "description": get_meta(soup, "twitter:description"),
        "card": get_meta(soup, "twitter:card"),
    }

    title = get_title(soup)
    meta_desc = get_meta(soup, "description")
    canonical = get_canonical(soup, base_url)

    # Remove chrome, focus on content
    clean_soup(soup)
    main = pick_main_node(soup)

    # Headings
    h1s = [h.get_text(" ", strip=True) for h in main.find_all("h1")]
    h2s = [h.get_text(" ", strip=True) for h in main.find_all("h2")]
    h3s = [h.get_text(" ", strip=True) for h in main.find_all("h3")]

    # Text (visible)
    text = text_from_node(main)
    page_hash = hashlib.sha256((text or "").encode("utf-8")).hexdigest() if text else None

    # Simple facts
    emails = sorted(set(EMAIL_RE.findall(text or "")))
    phones = sorted(set(PHONE_RE.findall(text or "")))
    money = sorted(set(MONEY_RE.findall(text or "")))
    dates = sorted(set(DATE_RE.findall(text or "")))

    # Links, breadcrumbs, JSON-LD types
    links_summary = extract_links(soup, base_url)
    breadcrumbs = get_breadcrumbs(soup)
    jsonld_types = extract_json_ld_types(soup)

    return {
        "title": title,
        "meta_description": meta_desc,
        "canonical_url": canonical,
        "lang": lang,
        "meta_robots": meta_robots,
        "meta_generator": meta_generator,
        "og": og,
        "twitter": twitter,
        "h1": h1s,
        "h2": h2s,
        "h3": h3s,
        "text": text,
        "word_count": len(text.split()) if text else 0,
        "emails": emails,
        "phones": phones,
        "money_amounts": money,
        "dates": dates,
        "links": links_summary,
        "breadcrumbs": breadcrumbs,
        "structured_data_types": jsonld_types,
        "page_hash": page_hash,
    }

# --------- Main pipeline ---------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_urls", default=DEFAULT_IN_URLS)
    ap.add_argument("--in_labels", default=DEFAULT_IN_LABELS)
    ap.add_argument("--out_jsonl", default=DEFAULT_OUT_JSONL)
    ap.add_argument("--max", type=int, default=0, help="Optional cap for quick tests")
    args = ap.parse_args()

    urls = [norm_url(u) for u in load_url_list(args.in_urls)]
    labels = load_labels(args.in_labels)
    done = already_scraped(args.out_jsonl)

    if args.max:
        urls = urls[:args.max]

    os.makedirs(os.path.dirname(args.out_jsonl), exist_ok=True)

    with requests.Session() as session, open(args.out_jsonl, "a", encoding="utf-8") as out:
        for i, url in enumerate(urls, 1):
            url_norm = norm_url(url)
            if not url_norm or url_norm in done:
                continue
            if is_skipped(url_norm):
                continue

            # polite delay
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

            try:
                status, ctype, html, final_url = fetch(session, url_norm)
            except Exception as e:
                rec = {
                    "url": url_norm,
                    "fetched_at": utc_now_z(),
                    "error": f"{type(e).__name__}: {e}",
                }
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out.flush()
                continue

            meta = {
                "url": url_norm,
                "final_url": final_url,
                "status_code": status,
                "content_type": ctype,
                "fetched_at": utc_now_z(),
            }

            # Record non-HTML responses and skip parsing
            if not (200 <= status < 300) or not is_html_content_type(ctype):
                rec = {"meta": meta}
                # Join category metadata if we have it
                if url_norm in labels:
                    rec.update(labels[url_norm])
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out.flush()
                continue

            # Parse HTML
            try:
                parsed = parse_html(html, final_url or url_norm)
            except Exception as e:
                rec = {
                    "meta": meta,
                    "url": url_norm,
                    "fetched_at": utc_now_z(),
                    "parse_error": f"{type(e).__name__}: {e}",
                }
                if url_norm in labels:
                    rec.update(labels[url_norm])
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out.flush()
                continue

            rec = {
                "meta": meta,
                "url": url_norm,
                **parsed,
            }
            # Join category metadata
            if url_norm in labels:
                rec.update(labels[url_norm])

            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()

if __name__ == "__main__":
    main()
