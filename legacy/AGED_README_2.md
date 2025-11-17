# 🧩 MDC Data Curation & Web Scraping Pipeline  
### *Miami Dade College – Applied AI / NLP Project*  
**Author:** Garcet, Lorenzo A.  
**Team Members:** Duran, Fabrizio Andres   
**Team Members:** Lopez Jr., Jorge  
**Team Members:** Martinez III, Miguel Angel  
**Version:** v1.2.2 (Crawler), 1.0 (Legacy/ Old Pipeline Tools Provided by MDC)  
**Last Updated:** 2025-11-16

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

### **2. Business-Grade Crawler Pipeline (v0.2.1)**  
A modern, production-style crawler (`crawler.py`) that discovers MDC pages automatically, filters bad links, logs errors, and outputs a comprehensive list of real HTML pages.

Documentation for new pipeline was created, the legacy pipeline did not include a markdown.
```
Category URLs counts v0.1.1 (file: ../aged_data_files/url_with_category_v1.csv):
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
```

```
Category URLs counts v0.1.1 (file: ../data/url_with_category_v3.csv)
HTML category counts:
  Other/Uncategorized            3308
  Library & Research             3168
  Programs, Degrees & Catalog    2934
  Events & Calendar              1485
  Continuing Education (non-credit) 1435
  Campuses & Locations           1197
  News & Press                   1107
  Student Resources & Support    830
  Testing & Placement            406
  Advising & Registration        302
  Financial Aid & Scholarships   170
  Foundation & Alumni            158
  Costs & Payments               138
  Public Safety & Emergency      129
  MDC Online                     126
  Portals & Systems              122
  Career Services (MDC WORKS)    77
  Admissions & Getting Started   74
  International Students         66
  Veterans & Military            51
  Policies & Procedures          10

Wrote: ../data/urls_with_category_v3.csv
Wrote: ../data/target_links_v3.txt  (MVP categories only; HTML only)

PDF category counts:
  Other/Uncategorized            1047
  Policies & Procedures          422
  News & Press                   389
  Campuses & Locations           336
  Programs, Degrees & Catalog    222
  Testing & Placement            76
  Advising & Registration        64
  Admissions & Getting Started   49
  Costs & Payments               29
  Public Safety & Emergency      23
  MDC Online                     13
  Library & Research             11
  Financial Aid & Scholarships   8
  Career Services (MDC WORKS)    7
  Portals & Systems              4
  Continuing Education (non-credit) 3
  International Students         2

Wrote: ../data/pdfs_with_category_v3.csv           19
```

---

# ⚙️ Pipeline Summary

## **High-Level Workflow**

1. `crawler.py` → `../data/mdc_links_raw_v2.txt`
2. `link_cleaner.py (updated version)` → `../data/cleaned_links_v2.txt`
3. Next scripts (PDF remover / splitter / content scraper) should read from cleaned_links_v2.txt.

```
Versioning Section:
We follow a semantic versioning approach for this project:
    •    Major version (X.0.0): Significant feature updates or large changes.
    •    Minor version (X.Y.0): Smaller feature additions or enhancements.
    •    Patch version (X.Y.Z): Minor tweaks, bug fixes, or small adjustments.
```
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
  - `OUTPUT_LINKS_PATH: str = "../data/mdc_links_raw_v3.txt"`
  - `ERROR_LOG_PATH: str = "../data/mdc_crawler_errors_v3.log"`

### ✔ Sample output
[435] https://www.mdc.edu/academics/ - elapsed: 575.3s, frontier=92
STOPPED because max_pages (20000) was reached.
Saved 10000 URLs to ../data/mdc_links_raw_v1.txt

### Best Practice 
```
- Scheduled Crawler Runs: To minimize impact on the school’s website traffic, we run the crawler once a month during 
off-peak hours. For example, we start it around midnight and let it run until early morning (about 10 hours), ensuring 
we’re not overloading the network. 
- Polite Crawling: We include a one-second delay between requests to avoid flooding the server and to stay within 
respectful usage limits.
```
```
Note: seed max_page= 20,000 does not reach end of available links to explore, 
current time for the crawler 9 - 10 hours. To be run once a month during low network traffic times.
```


---
# 🧩 Detailed Script Documentation

## 1. `crawler.py` (v2.0)
### **Purpose**
Automatically crawl MDC’s public site and collect up to 20,000 HTML pages.

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
## 2. `link_cleaner.py` (v2.0)


---
## 3. `url_categorizer.py` (v2.0)

---
## 4. `page_scrapper.py` (v2.0)

---
## 5. `pdf_scrapper.py` (v2.0)

---
🏁 Summary
This repository now contains:

A modern, enterprise crawler

Legacy tools for backwards compatibility

A documented end-to-end data ingestion system

A clear roadmap for turning MDC’s website into an AI-ready dataset