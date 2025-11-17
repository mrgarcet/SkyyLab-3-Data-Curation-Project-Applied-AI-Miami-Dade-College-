#!/usr/bin/env python3
"""
pdf_scraper.py (v1.0.0)

Purpose
-------
Fetch PDFs from a list, robustly resolve Chrome-viewer HTML wrappers, extract text,
and write AI-ready JSONL with helpful metadata.

Inputs
------
  --in_pdfs     ../data/pdf_links_v3.txt               # list of candidate PDF URLs (one per line)
  --in_labels   ../data/pdfs_with_category_v3.csv      # optional labels CSV (url,category,confidence,reason)

Output
------
  --out_jsonl   ../data/mdc_pdfs_v3.jsonl

Behavior
--------
  - Polite delay (0.5–1.0 s) with retries
  - Resolves HTML "viewer" pages (e.g., Chrome PDF viewer) to the direct PDF URL:
      * <embed original-url="https://...pdf">
      * <object data="...pdf">, <iframe src="...pdf">, <a href="...pdf">
      * meta refresh → .pdf
      * regex fallback that finds any https?://...pdf in the HTML
  - Streams the file up to a configurable size (default 25 MB)
  - Extracts text (pdfplumber preferred; PyPDF2 fallback)
  - Outputs one JSON object per line including:
      url, final_url, status_code, content_type, fetched_at, file_size, file_sha256,
      page_count, word_count, text, emails, phones, money_amounts, dates,
      and (if present) PDF metadata (title/author/subject/creator/producer/created/modified)
  - Resume-friendly: skips URLs already present in the output JSONL

Install
-------
pip install requests beautifulsoup4 lxml pdfplumber PyPDF2

Run
---
python scraper/pdf_scraper.py \
  --in_pdfs ../data/pdf_links_v3.txt \
  --in_labels ../data/pdfs_with_category_v3.csv \
  --out_jsonl ../data/mdc_pdfs_v3.jsonl
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import random
import re
import time
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from datetime import datetime, UTC
import hashlib

# ---------- CLI defaults ----------
DEFAULT_IN_PDFS   = "../data/pdf_links_v3.txt"
DEFAULT_IN_LABELS = "../data/pdfs_with_category_v3.csv"
DEFAULT_OUT_JSONL = "../data/mdc_pdfs_v3.jsonl"

USER_AGENT = "SkyyScraper-PDF/1.0 (+https://example.org) contact: you@example.org"

DELAY_MIN = 0.5
DELAY_MAX = 1.0
TIMEOUT   = 30
RETRIES   = 2
MAX_MB    = 25  # refuse to fully download PDFs larger than this (approx)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/pdf,application/octet-stream;q=0.9,text/html;q=0.8,*/*;q=0.5",
}

# --------- Simple facts regex (same spirit as page scraper) ----------
RE_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
RE_PHONE = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")
RE_MONEY = re.compile(r"\$\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?")
RE_DATE  = re.compile(r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|"
                      r"May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|"
                      r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:,\s*\d{4})?\b")

def utc_now_z() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

# --------- I/O helpers ----------
def load_urls(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]

def load_labels(path: str) -> Dict[str, Dict[str, str]]:
    labels: Dict[str, Dict[str, str]] = {}
    if not os.path.exists(path):
        return labels
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            u = (row.get("url") or "").strip()
            if not u:
                continue
            labels[u] = {
                "category": (row.get("category") or "").strip(),
                "confidence": (row.get("confidence") or "").strip(),
                "reason": (row.get("reason") or "").strip(),
            }
    return labels

def already_scraped(path: str) -> Set[str]:
    seen: Set[str] = set()
    if not os.path.exists(path):
        return seen
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                u = obj.get("url")
                if u:
                    seen.add(u)
            except Exception:
                continue
    return seen

def write_jsonl(path: str, rec: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8") as out:
        out.write(json.dumps(rec, ensure_ascii=False) + "\n")

# --------- Network helpers ----------
def fetch_stream(session: requests.Session, url: str, max_mb: int = MAX_MB) -> Tuple[int, str, Optional[bytes], str, int, Optional[str]]:
    """
    Stream the response. Respect max_mb; stop downloading if exceeded.
    Returns: (status_code, content_type, data_or_None, final_url, bytes_read, stop_reason)
    stop_reason may be "too_large".
    """
    last_exc: Optional[Exception] = None
    for attempt in range(RETRIES + 1):
        try:
            with session.get(url, headers=HEADERS, stream=True, allow_redirects=True, timeout=TIMEOUT) as r:
                ctype = r.headers.get("Content-Type", "") or ""
                final_url = str(r.url)
                max_bytes = max_mb * 1024 * 1024 if max_mb > 0 else None

                buf = io.BytesIO()
                total = 0
                chunk_size = 64 * 1024
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if max_bytes and total > max_bytes:
                        return r.status_code, ctype, None, final_url, total, "too_large"
                    buf.write(chunk)

                data = buf.getvalue()
                return r.status_code, ctype, data, final_url, total, None
        except Exception as e:
            last_exc = e
            if attempt < RETRIES:
                time.sleep(0.6)
                continue
            raise e
    if last_exc:
        raise last_exc
    raise RuntimeError("Unreachable fetch_stream path")

def looks_like_pdf_bytes(data: bytes) -> bool:
    return data[:4] == b"%PDF"

# --------- HTML wrapper resolver ----------
PDF_URL_RE = re.compile(r"https?://[^\s\"'>]+\.pdf\b", re.I)

def find_pdf_url_in_html(html: str, base_url: str) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")

    # 1) Chrome viewer pattern from your screenshot: <embed original-url="...pdf">
    emb = soup.find("embed", attrs={"original-url": True})
    if emb:
        return urljoin(base_url, emb["original-url"])
    # Some sites use data-original-url
    emb2 = soup.find("embed", attrs={"data-original-url": True})
    if emb2:
        return urljoin(base_url, emb2["data-original-url"])

    # 2) <object data="...pdf"> or <iframe src="...pdf">
    obj = soup.find("object", attrs={"data": True})
    if obj and obj["data"].lower().endswith(".pdf"):
        return urljoin(base_url, obj["data"])
    iframe = soup.find("iframe", attrs={"src": True})
    if iframe and iframe["src"].lower().endswith(".pdf"):
        return urljoin(base_url, iframe["src"])

    # 3) Any <a href="...pdf">
    a = soup.find("a", href=re.compile(r"\.pdf($|\?)", re.I))
    if a:
        return urljoin(base_url, a["href"])

    # 4) meta refresh → .pdf
    meta = soup.find("meta", attrs={"http-equiv": re.compile("^refresh$", re.I)})
    if meta and meta.get("content"):
        m = re.search(r"url=(.+)$", meta["content"], flags=re.I)
        if m:
            cand = m.group(1).strip().strip("'\"")
            if cand.lower().endswith(".pdf"):
                return urljoin(base_url, cand)

    # 5) Last-resort regex scan
    m = PDF_URL_RE.search(html)
    if m:
        return urljoin(base_url, m.group(0))

    return None

# --------- PDF text extraction ----------
def extract_pdf_text(data: bytes) -> Tuple[str, Optional[int], Dict[str, Optional[str]]]:
    """
    Returns: (text, page_count, meta)
    meta keys: title, author, subject, creator, producer, created, modified
    """
    # Prefer pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = []
            for p in pdf.pages:
                try:
                    t = p.extract_text() or ""
                except Exception:
                    t = ""
                if t:
                    pages.append(t)
            txt = "\n\n".join(pages).strip()
            md = pdf.metadata or {}
            meta = {
                "title": md.get("Title"),
                "author": md.get("Author"),
                "subject": md.get("Subject"),
                "creator": md.get("Creator"),
                "producer": md.get("Producer"),
                "created": md.get("CreationDate") or md.get("Created"),
                "modified": md.get("ModDate") or md.get("Modified"),
            }
            return txt, len(pdf.pages), meta
    except Exception:
        pass

    # Fallback: PyPDF2
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(data))
        pages = []
        for p in reader.pages:
            try:
                t = p.extract_text() or ""
            except Exception:
                t = ""
            if t:
                pages.append(t)
        meta_obj = getattr(reader, "metadata", {}) or {}
        if isinstance(meta_obj, dict):
            md = meta_obj
        else:
            # Some versions expose a DocumentInformation-like object
            md = {}
            for k in ("title", "author", "subject", "creator", "producer", "creation_date", "modification_date"):
                v = getattr(meta_obj, k, None)
                if v:
                    md[k] = v
        meta = {
            "title": md.get("/Title") or md.get("title"),
            "author": md.get("/Author") or md.get("author"),
            "subject": md.get("/Subject") or md.get("subject"),
            "creator": md.get("/Creator") or md.get("creator"),
            "producer": md.get("/Producer") or md.get("producer"),
            "created": md.get("/CreationDate") or md.get("creation_date"),
            "modified": md.get("/ModDate") or md.get("modification_date"),
        }
        return "\n\n".join(pages).strip(), len(reader.pages), meta
    except Exception:
        return "", None, {}

# --------- Main ---------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_pdfs", default=DEFAULT_IN_PDFS)
    ap.add_argument("--in_labels", default=DEFAULT_IN_LABELS)
    ap.add_argument("--out_jsonl", default=DEFAULT_OUT_JSONL)
    ap.add_argument("--max", type=int, default=0, help="optional cap for quick tests")
    ap.add_argument("--max_mb", type=int, default=MAX_MB, help="max download size in MB")
    args = ap.parse_args()

    urls = load_urls(args.in_pdfs)
    if args.max and args.max > 0:
        urls = urls[:args.max]
    labels = load_labels(args.in_labels)
    done = already_scraped(args.out_jsonl)

    with requests.Session() as session:
        session.headers.update(HEADERS)

        for url in urls:
            if not url or url in done:
                continue

            # polite delay
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

            # 1) initial fetch
            try:
                status, ctype, data, final_url, nbytes, stop = fetch_stream(session, url, args.max_mb)
            except Exception as e:
                write_jsonl(args.out_jsonl, {
                    "url": url,
                    "fetched_at": utc_now_z(),
                    "error": f"{type(e).__name__}: {e}",
                })
                continue

            # If we hit size ceiling
            if stop == "too_large":
                rec = {
                    "url": url,
                    "final_url": final_url,
                    "status_code": status,
                    "content_type": ctype,
                    "fetched_at": utc_now_z(),
                    "file_size": nbytes,
                    "note": "too_large_to_download",
                }
                if url in labels:
                    rec.update(labels[url])
                write_jsonl(args.out_jsonl, rec)
                continue

            # If not bytes -> treat as error
            if data is None:
                rec = {
                    "url": url,
                    "final_url": final_url,
                    "status_code": status,
                    "content_type": ctype,
                    "fetched_at": utc_now_z(),
                    "note": "no_data",
                }
                if url in labels:
                    rec.update(labels[url])
                write_jsonl(args.out_jsonl, rec)
                continue

            # 2) Decide whether we already have a PDF
            pdf_data = None
            pdf_ct   = ctype
            pdf_url  = final_url

            if "application/pdf" in (ctype or "").lower() or looks_like_pdf_bytes(data) or pdf_url.lower().endswith(".pdf"):
                pdf_data = data
            else:
                # 3) HTML wrapper → look for the direct .pdf URL and fetch that
                try:
                    html_text = data.decode("utf-8", errors="ignore")
                except Exception:
                    html_text = ""
                direct = find_pdf_url_in_html(html_text, final_url or url)
                if direct:
                    # second fetch: direct PDF
                    try:
                        status2, ctype2, data2, final2, nbytes2, stop2 = fetch_stream(session, direct, args.max_mb)
                    except Exception as e:
                        write_jsonl(args.out_jsonl, {
                            "url": url,
                            "html_wrapper_final": final_url,
                            "resolved_pdf_candidate": direct,
                            "fetched_at": utc_now_z(),
                            "error": f"{type(e).__name__}: {e}",
                        })
                        continue

                    if stop2 == "too_large":
                        rec = {
                            "url": url,
                            "html_wrapper_final": final_url,
                            "resolved_pdf_candidate": direct,
                            "final_url": final2,
                            "status_code": status2,
                            "content_type": ctype2,
                            "fetched_at": utc_now_z(),
                            "file_size": nbytes2,
                            "note": "too_large_to_download",
                        }
                        if url in labels:
                            rec.update(labels[url])
                        write_jsonl(args.out_jsonl, rec)
                        continue

                    if data2 and ("application/pdf" in (ctype2 or "").lower() or looks_like_pdf_bytes(data2) or final2.lower().endswith(".pdf")):
                        pdf_data = data2
                        pdf_ct   = ctype2
                        pdf_url  = final2
                    else:
                        # Not a PDF even after resolving
                        rec = {
                            "url": url,
                            "html_wrapper_final": final_url,
                            "resolved_pdf_candidate": direct,
                            "final_url": final2,
                            "status_code": status2,
                            "content_type": ctype2,
                            "fetched_at": utc_now_z(),
                            "note": "resolved_but_not_pdf",
                        }
                        if url in labels:
                            rec.update(labels[url])
                        write_jsonl(args.out_jsonl, rec)
                        continue
                else:
                    # No direct PDF found in HTML
                    rec = {
                        "url": url,
                        "final_url": final_url,
                        "status_code": status,
                        "content_type": ctype,
                        "fetched_at": utc_now_z(),
                        "note": "html_wrapper_no_pdf_link_found",
                    }
                    if url in labels:
                        rec.update(labels[url])
                    write_jsonl(args.out_jsonl, rec)
                    continue

            # 4) At this point, we have pdf_data
            file_size = len(pdf_data) if pdf_data else 0
            file_sha256 = hashlib.sha256(pdf_data).hexdigest() if pdf_data else None

            text, page_count, meta = extract_pdf_text(pdf_data)
            word_count = len(text.split()) if text else 0

            emails = sorted(set(RE_EMAIL.findall(text or "")))
            phones = sorted(set(RE_PHONE.findall(text or "")))
            money  = sorted(set(RE_MONEY.findall(text or "")))
            dates  = sorted(set(RE_DATE.findall(text or "")))

            rec = {
                "url": url,
                "final_url": pdf_url,
                "status_code": 200,                 # we reached a valid PDF
                "content_type": pdf_ct,
                "fetched_at": utc_now_z(),
                "file_size": file_size,
                "file_sha256": file_sha256,
                "page_count": page_count,
                "word_count": word_count,
                "text": text,
                "emails": emails,
                "phones": phones,
                "money_amounts": money,
                "dates": dates,
                "pdf_meta": meta,                   # may include title/author/created/modified
            }
            if url in labels:
                rec.update(labels[url])

            write_jsonl(args.out_jsonl, rec)

if __name__ == "__main__":
    main()
