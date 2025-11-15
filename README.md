# 🧩 MDC Data Curation & Web Scraping Pipeline  
### *Miami Dade College – Applied AI / NLP Project*  
**Author:** Lorenzo Garcet  
**Version:** 2.0 (Crawler), 1.0 (Legacy Tools Provided by MDC)  
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

Both workflows are documented below.

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
STOPPED because max_pages (2000) was reached.
Saved 2000 URLs to ../data/mdc_links_raw_v1.txt

yaml
Copy code

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

markdown
Copy code

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

2. link_cleaner.py
Removes fragments & duplicate entries.

Functions
clean_links(url)

create_list_without_duplicates(list)

append_list_to_file(list, file)

Output: cleaned_links_set.txt

3. link_cleaner_v0.0.2.py
Improved version using Python literal strings for interoperability.

Recommended version to use ✔
Why: Compatible with ast.literal_eval().

4. pdf_remover.py
Filters .pdf references from cleaned link list.

Reads
cleaned_links_set.txt

Writes
no_pdf_list.txt

5. list_divider.py
Used in the legacy pipeline to divide scraped URLs into three scraping batches.

Outputs:
no_pdf_list_div1.txt

no_pdf_list_div2.txt

no_pdf_list_div3.txt

6. p_tag_scrapper.py
Fetches URLs and extracts <p> paragraphs into text files.

⚠️ Known bug:

python
Copy code
index =+ 1  # wrong
index += 1  # correct
📁 Data Flow Diagram (All Systems)
mermaid
Copy code
flowchart TD

%% Crawler v2
A1[SEED_URLS: https://www.mdc.edu/] --> B1[crawler.py]
B1 --> C1[mdc_links_raw_v2.txt]
B1 --> D1[mdc_crawler_errors_v2.log]

%% Legacy pipeline
C2[processed_mdc_links.txt] --> D2[link_cleaner_v0.0.2.py]
D2 --> E2[cleaned_links_set.txt]
E2 --> F2[pdf_remover.py]
F2 --> G2[no_pdf_list.txt]
G2 --> H2[list_divider.py]
H2 --> I2[div1/div2/div3]
I2 --> J2[p_tag_scrapper.py]
J2 --> K2[link_#.txt]
🧰 Dependencies
Install required Python libraries:

bash
Copy code
pip install requests beautifulsoup4
🚀 How to Run the New Crawler
bash
Copy code
python crawler.py
Results saved to:

../data/mdc_links_raw_v2.txt

../data/mdc_crawler_errors_v2.log

🧾 Future Output Format (Planned JSONL)
For AI/NLP, each page will eventually be stored as:

json
Copy code
{
  "url": "https://www.mdc.edu/example/",
  "title": "Example Page",
  "headings": ["Header 1", "Header 2"],
  "text": "... extracted text ...",
  "last_seen": "2025-11-14",
  "tags": ["admissions", "degree_program"]
}
🧩 Recommended Improvements (Roadmap)
✔ Replace raw text lists with JSON or JSONL
✔ Add retries/backoff logic in crawler
✔ Automate nightly crawls
✔ Build page scraper using BeautifulSoup
✔ Build curated / tagged dataset
✔ Add vector embeddings (OpenAI/HF models)
✔ Build search & Q&A layer for Skyy AI
🧭 Business Context
This pipeline enables MDC to:

Maintain an authoritative digital knowledge base

Power AI student assistants

Provide program discovery tools

Enable robust search over degrees/courses

Reduce administrative load

Improve student experience and retention

🏁 Summary
This repository now contains:

A modern, enterprise crawler

Legacy tools for backwards compatibility

A documented end-to-end data ingestion system

A clear roadmap for turning MDC’s website into an AI-ready dataset