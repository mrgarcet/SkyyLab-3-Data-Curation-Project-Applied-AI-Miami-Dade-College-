# 🧩 MDC Data Curation & Web Scraping Pipeline
### *Miami Dade College – Applied AI / NLP Project*

**Author:** `Garcet, Lorenzo A.`  
**Team Members:** `Duran, Fabrizio Andres` · `Lopez Jr., Jorge` · `Martinez III, Miguel Angel`

**Component Versions (from source):**
- `pipeline/crawler.py` — **v0.2.1**
- `pipeline/link_cleaner.py` — **v0.2.1**
- `pipeline/url_categorizer.py` — **v0.2.2**
- `scraper/page_scrapper.py` (file name) / “page_scraper.py” (module title) — **v1.0.0**
- `scraper/pdf_scraper.py` — **v1.0.0**
- Legacy tools (in `/legacy`) — historical utilities provided by MDC

**Data Snapshot Label:** **v3** (matches current file names in `/data`)  
**Last Updated:** **2025‑11‑17**

---

## 📘 Overview

This repository implements a **repeatable, resilient pipeline** to build an AI‑ready knowledge base from the public website of **Miami Dade College (mdc.edu)**.

Instead of a rigid, page‑structure‑dependent scraper, we intentionally split the process into **independent stages**:

1. **Collect** — crawl and record *all* discoverable on‑domain URLs (including PDFs).
2. **Clean** — normalize URLs, remove duplicates and junk, and split **HTML vs PDF**.
3. **Categorize** — tag URLs by topic (e.g., Admissions, Financial Aid) to support targeted curation and scrape priority.
4. **Extract** — scrape structured content from HTML pages and text from PDFs into **line‑delimited JSON**.

> **Why this design?**  
> MDC’s site changes often. By **decoupling** discovery, cleaning, categorization, and extraction, the pipeline remains **adaptable** if pages or layouts change. Each stage can be **re‑run periodically** (e.g., on a schedule), and outputs are versioned (current **v3**) to keep historical snapshots. The result is a **scalable** system that won’t break on minor HTML changes and that supports incremental refreshes.

---

## ⚙️ High‑Level Workflow

1. `pipeline/crawler.py` → `data/mdc_links_raw_v3.txt` (+ `data/mdc_crawler_errors_v3.log`)  
2. `pipeline/link_cleaner.py` → `data/html_links_v3.txt` and `data/pdf_links_v3.txt`  
3. `pipeline/url_categorizer.py`  
   - HTML: → `data/urls_with_category_v3.csv` + **targets** → `data/target_links_v3.txt`  
   - PDF (optional): → `data/pdfs_with_category_v3.csv`  
4. `scraper/page_scrapper.py` → `data/mdc_pages_v3.jsonl`  
5. `scraper/pdf_scraper.py` → `data/mdc_pdfs_v3.jsonl`

All JSON outputs are **line‑delimited** (one JSON object per line) and safe to append for resumable runs.

---

## 📂 Repository Contents
```
**Skyy
¦   README.md
¦   requirements.txt
¦               
+---aged_data_files
¦       cleaned_links_v2.txt
¦       mdc_crawler_errors.log
¦       mdc_crawler_errors_v2.log
¦       mdc_links_raw.txt
¦       mdc_links_raw_v2.txt
¦       mdc_pages_v3.jsonl
¦       target_links_v1.txt
¦       urls_with_category_v1.csv
¦       
+---data
¦       html_links_v3.txt
¦       mdc_crawler_errors_v3.log
¦       mdc_links_raw_v3.txt
¦       mdc_pages_v3.jsonl
¦       mdc_pdfs_v3.jsonl
¦       pdfs_with_category_v3.csv
¦       pdf_links_v3.txt
¦       target_links_v3.txt
¦       urls_with_category_v3.csv
¦       
+---docs
¦       changelog.md
¦       
+---legacy
¦   ¦   legacy__README.md
¦   ¦   
¦   +---data
¦   ¦       legacy_cleaned_links_set.txt
¦   ¦       legacy_no_pdf_list.txt
¦   ¦       legacy_no_pdf_list_div1.txt
¦   ¦       legacy_no_pdf_list_div2.txt
¦   ¦       legacy_no_pdf_list_div3.txt
¦   ¦       legacy_processed_mdc_links.txt
¦   ¦       
¦   +---scrapper
¦   ¦       legacy_link_cleaner.py
¦   ¦       legacy_link_cleaner_v0.0.2.py
¦   ¦       legacy_list_divider.py
¦   ¦       legacy_pdf_remover.py
¦   ¦       legacy_p_tag_scrapper.py
¦   ¦       
¦   +---__MACOSX
¦       +---data
¦       ¦       ._cleaned_links_set.txt
¦       ¦       ._processed_mdc_links.txt
¦       ¦       
¦       +---scrapper
¦               ._link_cleaner.py
¦               ._link_cleaner_v0.0.2.py
¦               ._p_tag_scrapper.py
¦               
+---pipeline
¦       crawler.py
¦       link_cleaner.py
¦       url_categorizer.py
¦       
+---scraper
        page_scrapper.py
        pdf_scraper.py
```

---

**What lives where (quick guide):**
- **`/pipeline`** — modern pipeline components:
  - `crawler.py` (v0.2.1) — on‑domain URL discovery, error logging
  - `link_cleaner.py` (v0.2.1) — normalization, de‑dup, split HTML/PDF
  - `url_categorizer.py` (v0.2.2) — rule‑based topic labeling + target list
- **`/scraper`** — content extraction:
  - `page_scrapper.py` (v1.0.0) — HTML page parsing → `mdc_pages_v3.jsonl`
  - `pdf_scraper.py` (v1.0.0) — PDF fetch + text extraction → `mdc_pdfs_v3.jsonl`
- **`/data`** — **current v3** inputs/outputs for the latest run(s)
- **`/aged_data_files`** — historical artifacts from earlier versions (v1/v2)
- **`/legacy`** — original MDC utilities (kept for reference/backward compatibility)
- **`/docs/changelog.md`** — incremental notes and version bumps (author updates)

> ✅ The pipeline scripts default to reading/writing relative to `../data/` from their own folder, which matches this layout.

---

## 🚀 Quick Start

This project is designed to run as a **repeatable pipeline** so you can re‑crawl and re‑ingest MDC (mdc.edu) content as the website evolves without brittle assumptions. The flow is: **crawl → clean → categorize → scrape HTML → scrape PDFs**. Defaults are already wired to the `data/` folder.

### 1) Prereqs
- **Python 3.11+** (recommended; code uses modern `datetime.UTC` and 3.12‑safe patterns)
- **pip** available on PATH

### 2) Create & activate a virtual environment
**Windows (PowerShell)**
```powershell
(.venv) C:\SkyyLab>
pip --version
pip install requests beautifulsoup4 lxml


```

### 3) Install Dependencies
`pip install -r requirements.txt`

### 4) Run the pipeline  
All scripts have sensible defaults and write into the data/ directory:  
`python pipeline/crawler.py`


---
# Run the pipeline (end‑to‑end):
## 1) Crawl
python pipeline/crawler.py

## 2) Clean and split HTML/PDF
python pipeline/link_cleaner.py

## 3) Categorize (HTML required; PDF optional)
python pipeline/url_categorizer.py \
  --input ../data/html_links_v3.txt \
  --out-csv ../data/urls_with_category_v3.csv \
  --out-txt ../data/target_links_v3.txt \
  --pdf ../data/pdf_links_v3.txt \
  --pdf-out-csv ../data/pdfs_with_category_v3.csv

## 4) Scrape HTML pages (MVP categories)
python scraper/page_scrapper.py \
  --in_urls ../data/target_links_v3.txt \
  --in_labels ../data/urls_with_category_v3.csv \
  --out_jsonl ../data/mdc_pages_v3.jsonl

## 5) Scrape PDFs (optional, recommended)
python scraper/pdf_scraper.py \
  --in_pdfs ../data/pdf_links_v3.txt \
  --in_labels ../data/pdfs_with_category_v3.csv \
  --out_jsonl ../data/mdc_pdfs_v3.jsonl

---
# 🧩 Detailed Script Documentation
1) `pipeline/crawler.py` — v0.2.1

## **Purpose**  
On‑domain crawler for `mdc.edu`. Starts at `https://www.mdc.edu/`, follows internal links, and emits one URL per line
for downstream processing.

**Key defaults & paths**  
- Seeds: `["https://www.mdc.edu/"]`  
- Domain scope: `mdc.edu`  
- Max pages: `DEFAULT_MAX_PAGES = 20000`  
- Politeness: `REQUEST_DELAY = 1.0s, REQUEST_TIMEOUT = 20s`    
- Output: `../data/mdc_links_raw_v3.txt`  
- Errors: `../data/mdc_crawler_errors_v3.log`

- Skips (examples):  
  - **Disallowed prefixes:** `/newsandnotes/`  `/trackback/` `/publications/` `/email/`
  - **Extensions:** images, office docs, archives, media; PDFs are allowed in v3  
  - **Known junk:** calendar event confirmation links; generic Shibboleth/auth endpoints

## Behavior

- Normalizes URLs (drops fragments).  
- De‑dupes during crawl.
- Writes all discovered URLs to the raw list upon completion. 

---
2) `pipeline/link_cleaner.py` — v0.2.1

# Purpose
Consume `mdc_links_raw_v3.txt` and produce two de‑duplicated, normalized lists:
- `../data/html_links_v3.txt`
- `../data/pdf_links_v3.txt`

## What it does
- Trims whitespace and fragments.
- Removes clear junk (logins, confirms, off‑domain).
- Keeps `.pdf` URLs by design (handled separately).
- Splits by extension using a simple `get_extension()` helper.

## I/O (fixed paths)
- In: `../data/mdc_links_raw_v3.txt ` 
- Out: `../data/html_links_v3.txt`, `../data/pdf_links_v3.txt`

Runs as a script; no CLI flags in this version.

---
3) `pipeline/url_categorizer.py` — v0.2.2

# Purpose
Rule‑based categorization of URLs to support targeted scraping and downstream curation.

## Inputs / Outputs (defaults)
- HTML
  - In: `../data/html_links_v3.txt`
  - Out: `../data/urls_with_category_v3.csv` (columns: url, category, confidence, reason)
  - Targets (MVP only): `../data/target_links_v3.txt`
- PDF (optional)
  - In: `../data/pdf_links_v3.txt`
  - Out: `../data/pdfs_with_category_v3.csv`
  - Optional targets: `--pdf-out-txt <path>`

## MVP Categories (built‑in set)
- Admissions & Getting Started
- Advising & Registration
- Testing & Placement
- Costs & Payments
- Financial Aid & Scholarships
- Programs, Degrees & Catalog
- Student Resources & Support
- Library & Research
- Career Services (MDC WORKS)
- Continuing Education (non-credit)
- MDC Online
- International Students
- Veterans & Military
- Campuses & Locations

## How it works
- Combines path‑regex and keyword heuristics to propose categories.
- Scores candidates and prefers MVP categories on ties.
- Writes a labeled CSV including a confidence and reason field.
- Writes target_links_v3.txt with HTML links in MVP categories for the HTML scraper.

---
4) `scraper/page_scrapper.py` — v1.0.0
(File name uses “scrapper”; internal module title says “page_scraper.py”. See naming note below.)

## Purpose
MVP HTML scraper for MDC pages. Joins in category labels and writes **line‑delimited JSON** records.

##Inputs / Outputs (defaults)
- In URLs: `../data/target_links_v3.txt`
- In labels: `../data/urls_with_category_v3.csv`
- Out JSONL: `../data/mdc_pages_v3.jsonl`

## Fetcher settings  
- User‑Agent: `"SkyyScraper/1.0 contact: lorenzo.garcet001@mymdc.net"`
- Timeout: 25s · Retries: 2 · Delay: 0.5–1.0s between requests
- Skips auth/portal frames (e.g., PeopleSoft, SSO) via regex patterns

## Extraction (per page)
- meta: `{ url, final_url, status_code, content_type, fetched_at }`
- Core: `title`, `meta_description`, `canonical_url`, `lang`, `meta_robots`, `meta_generator`
- Social: `og{title,description,type,url}`, `twitter{title,description,card}`
- Headings: arrays of `h1`, `h2`, `h3`
- Main text and word_count
- Contact facts: `emails`, `phones`, `money_amounts`, `dates` (regex‑based)
- Structure: `breadcrumbs`, `structured_data_types` (from JSON‑LD), and link summary:
  - `internal_count/external_count/pdf_count/...` plus small samples and basic CTA anchors
- Label join: `merges category`, `confidence`, `reason` if present
- Resumable: skips URLs already present in the output JSONL

## Error handling
- Non‑HTML or HTTP errors: writes a minimal record with meta only
- Parse errors: records parse_error

---
5) `scraper/pdf_scraper.py` — v1.0.0

# Purpose
Fetch PDFs, robustly resolve browser viewer pages to the actual PDF URL, extract text, and write **line‑delimited JSON.**

## Inputs / Outputs (defaults)
- In PDFs: `../data/pdf_links_v3.txt`
- In labels: `../data/pdfs_with_category_v3.csv` (optional)
- Out JSONL: `../data/mdc_pdfs_v3.jsonl`

## Fetcher settings
- User‑Agent: `"SkyyScraper-PDF/1.0 (+https://example.org) contact: you@example.org"` (placeholder in code; update if needed)
- Timeout: 30s · Delay: 0.5–1.0s · Streamed download with size cap (`--max_mb`, default 25 MB)

## Viewer/Wrapper resolution
- Detects `<embed original-url="...pdf">`, `<object data="...pdf">`, `<iframe src="...pdf">`, links to `.pdf`
- Handles `meta refresh` and a final regex scan for any `https://...pdf` in HTML

## Text extraction
- **pdfplumber** preferred; **PyPDF2** fallback
- **Extracted fields include:**
  - `url`, `final_url`, `status_code`, `content_type`, `fetched_at`
  - `file_size`, `file_sha256`, `page_count`, `word_count`
  - `text`, `plus derived emails`, `phones`, `money_amounts`, `dates`
  - `pdf_meta` (e.g., title/author/created/modified when available)
  - Category labels merged when provided

---
# 🗂️ Current Data Artifacts (v3)

**From /data:**
- Discovery & cleaning
  - `mdc_links_raw_v3.txt` — all discovered links
  - `html_links_v3.txt` / `pdf_links_v3.txt` — cleaned, split
  - `mdc_crawler_errors_v3.log` — crawler issues
- Categorization
  - `urls_with_category_v3.csv` — HTML URLs with labels
  - `target_links_v3.txt` — HTML targets for MVP scraping
  - `pdfs_with_category_v3.csv` — labeled PDF URLs
- Scraped outputs
  - `mdc_pages_v3.jsonl` — HTML page records (line‑delimited JSON)
  - `mdc_pdfs_v3.jsonl` — PDF records (line‑delimited JSON)
`/aged_data_files` keeps v1/v2 era inputs/outputs for historical reference.

---
# 🗓️ Running Periodically
The pipeline is designed for scheduled runs (e.g., nightly/weekly):
- Re‑run **crawler** → **cleaner** → **categorizer** to refresh target lists as the site changes.
- **Scrapers** are idempotent/resumable (HTML scraper skips URLs already present in the output). 

You can orchestrate this with your preferred scheduler (cron, task runner, CI), keeping the /data versioned (`v4`, `v5`, …)
as needed.

---

