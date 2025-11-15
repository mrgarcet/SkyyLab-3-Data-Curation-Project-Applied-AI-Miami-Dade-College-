# 🧩 MDC Data Curation & Web Scraping Pipeline  
### *Miami Dade College – Applied AI / NLP Project*  
**Author:** Lorenzo Garcet  
**Version:** 2.0 (Crawler), 1.0 (Legacy/ Old Pipeline Tools Provided by MDC)  
**Last Updated:** 2025-11-14

---

# 📘 Overview

This repository contains the **full data ingestion pipeline** for building a structured knowledge base from the Miami Dade College (MDC) website.  
The goal is to collect, clean, organize, and structure MDC’s public-facing content to support:

- AI assistants (Skyy project)  
- NLP modeling  
- Data analysis  
- Program discovery tools  
- Student-facing Q&A systems  

Two systems exist in this repository:

### **1. Legacy Pipeline (v1)**  
Started with an externally-provided list of URLs and used scripts to clean, filter, divide, and scrape `<p>` tags into text files.

### **2. Business-Grade Crawler Pipeline (v2)**  
A modern, production-style crawler (`crawler.py`) that discovers MDC pages automatically, filters bad links, logs errors, and outputs a comprehensive list of real HTML pages.

Documentation for new pipeline, legacy pipeline noted.

Category URLs counts:
  other           7188
  events          664
  campus          594
  about           367
  student_services 327
  program_info    303
  financial_aid   219
  faculty_staff   135
  admissions      123
  library         25
  degree_page     19
  course_catalog  13
  news            12
  online_tools    10


---

# ⚙️ Pipeline Summary

## **High-Level Workflow**

1. `crawler.py` → `../data/mdc_links_raw_v2.txt`
2. `link_cleaner.py (updated version)` → `../data/cleaned_links_v2.txt`
3. Next scripts (PDF remover / splitter / content scraper) should read from cleaned_links_v2.txt.

---

# 🆕 **New Business-Grade Crawler (v2.0)**

`crawler.py` is a **production-style, polite, domain-restricted crawler** that automatically discovers MDC content.

### ✔ Features
- Crawls only `*.mdc.edu` domains  
- Skips login URLs, confirm endpoints, and JS-driven junk  
- Avoids PDFs, images, docs, media  
- Follows robots.txt disallow rules  
- Logs errors and status codes  
- Tracks crawl progress (elapsed time + frontier size)  
- Detects reason for stop:
  - True end of website  
  - Hit the `DEFAULT_MAX_PAGES` limit seed set to: 10,0000
- Outputs versioned datasets:
  - `mdc_links_raw_v1.txt`
  - `mdc_links_raw_v2.txt`

### ✔ Sample output
[435] https://www.mdc.edu/academics/ - elapsed: 575.3s, frontier=92
STOPPED because max_pages (10000) was reached.
Saved 10000 URLs to ../data/mdc_links_raw_v1.txt

`Note: seed max_page= 10,000 does not reach end of available links to explore, 
current time for the crawler 5.5 - 6 hours. To be run once a month during low network traffic times.`
---

# 🧠 Legacy Pipeline Detail (v1)

This pipeline was the original implementation before the crawler was introduced.

processed_mdc_links.txt
│ (raw list with duplicates & #fragments)
▼
link_cleaner_v0.0.2.py
│ (removes fragments & duplicate URLs)
▼
cleaned_links_set.txt
│ (clean list)
▼
pdf_remover.py
│ (removes .pdf)
▼
no_pdf_list.txt
│
▼
list_divider.py
│ (splits into div1/div2/div3)
▼
p_tag_scrapper.py
│ (extracts <p> text → link_#.txt)


---

# 📂 Repository Contents

| File / Folder | Type | Description |
|---------------|-------|-------------|
| `crawler.py` | Script | Business-grade crawler (v2). Discovers real MDC pages. |
| `mdc_links_raw_v1.txt` | Data | First crawl (2000 pages, hit cap). |
| `mdc_links_raw_v2.txt` | Data | Second crawl (10,000 page limit). |
| `mdc_crawler_errors_v*.log` | Log | Errors: 401, 403, 404, SSL errors, timeouts. |
| `processed_mdc_links.txt` | Data | Legacy pipeline raw URL list. |
| `link_cleaner.py` | Script | Removes #fragments + duplicates. |
| `link_cleaner_v0.0.2.py` | Script | Improved cleaner using Python literal strings. |
| `cleaned_links_set.txt` | Data | Deduplicated URL list. |
| `pdf_remover.py` | Script | Filters PDF links from cleaned list. |
| `no_pdf_list.txt` | Data | HTML-only link list. |
| `list_divider.py` | Script | Divides link lists into batches. |
| `p_tag_scrapper.py` | Script | Scrapes `<p>` tags into individual files. |
| `link_#.txt` | Data | Extracted text from individual pages (legacy method). |


---

# 🧩 Detailed Script Documentation

## 1. `crawler.py` (v2.0)
### **Purpose**
Automatically crawl MDC’s public site and collect up to 10,000 HTML pages.

### **Key Internals**
- `normalize_url()` → removes `#fragment`
- `should_skip_url()` → filters auth/confirm URLs
- `is_disallowed_path()` → respects robots.txt
- `has_skipped_extension()` → skips non-HTML

### **Configuration**
```python
DEFAULT_MAX_PAGES = 10000
REQUEST_TIMEOUT = 20
REQUEST_DELAY = 1.0
ALLOWED_DOMAIN_SUFFIX = "mdc.edu"
Output
../data/mdc_links_raw_v2.txt

../data/mdc_crawler_errors_v2.log
```
### ***Notes***
1. The crawler (v2) ignore pdf links, which cause missing the links for degree program breakdown
of the classes needed in order to complete the degree plan, this is something that need to be adjusted at a later time.
This is important information that would be beneficial to have with the scope of the project.
2. Crawler was ran as (v2) with `default_max_pages=1000` seed adjusted to 20000 to ensure addition space was allocated to account for PDFs linsk.
---
## 1. `link_cleaner` (v2.0)

---
🏁 Summary
This repository now contains:

A modern, enterprise crawler

Legacy tools for backwards compatibility

A documented end-to-end data ingestion system

A clear roadmap for turning MDC’s website into an AI-ready dataset