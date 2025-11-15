"""
url_categorizer.py (v0.2.1)

Goal:
- Read cleaned_links_v2.txt (one URL per line)
- Categorize each URL based on simple patterns (path, subdomain)
- Save:
    - urls_with_category_v1.csv  (url,category)
    - target_links_v1.txt        (subset of URLs in categories we care about)
- Print a summary of how many URLs fall in each category.

Run this AFTER link_cleaner.py and BEFORE building the full scraper.
"""

import os
import csv
from urllib.parse import urlparse

# --------- CONFIG ---------

INPUT_CLEAN_PATH = "../data/cleaned_links_v2.txt"
OUTPUT_CSV_PATH = "../data/urls_with_category_v1.csv"
OUTPUT_TARGET_PATH = "../data/target_links_v1.txt"

# Categories we care about for FIRST scraping pass
TARGET_CATEGORIES = {
    "program_info",
    "degree_page",
    "course_catalog",
    "student_services",
    "admissions",
    "financial_aid",
}

# Simple pattern-based rules.
# Each entry is (category_name, [list_of_substring_patterns])
# If any pattern appears in the URL path (or netloc in some cases), we assign that category.
CATEGORY_RULES = [
    ("program_info", [
        "/academics/programs",
        "/academic-programs",
        "/programs/",
        "/program/",
        "/schools/",
        "/school-of-",
    ]),
    ("degree_page", [
        "/aa-",
        "/as-",
        "/aas-",
        "/bachelor-",
        "/baccalaureate",
        "/degree/",
        "/degrees/",
        "/certificates/",
        "/certificate/",
    ]),
    ("course_catalog", [
        "/courses/",
        "/course-descriptions",
        "/course-catalog",
        "/catalog/",
    ]),
    ("student_services", [
        "/student-services",
        "/students/services",
        "/advisement",
        "/counseling",
        "/tutoring",
        "/career-services",
        "/registration",
        "/testing",
    ]),
    ("admissions", [
        "/admissions",
        "/apply/",
        "/enrollment",
        "/enroll/",
    ]),
    ("financial_aid", [
        "/financial-aid",
        "/scholarship",
        "/scholarships",
        "/tuition",
        "/paying-for-college",
    ]),
    ("faculty_staff", [
        "/faculty",
        "/staff",
        "/directory",
    ]),
    ("events", [
        "/calendar",
        "/events/",
        "/event/",
    ]),
    ("news", [
        "/news/",
        "/stories/",
        "/press/",
    ]),
    ("campus", [
        "/campus/",
        "/campuses/",
        "/wolfson",
        "/kendall",
        "/hialeah",
        "/homestead",
        "/north-campus",
        "/west-campus",
        "/padrón",
        "/padron",
    ]),
    ("library", [
        "/library",
        "/libraries",
    ]),
    ("online_tools", [
        "/blackboard",
        "/canvas",
        "/portal",
        "/login",
        "mdc.blackboard.com",
    ]),
    ("about", [
        "/about",
        "/mission",
        "/vision",
        "/history",
        "/leadership",
    ]),
]


def load_urls(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Input file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def categorize_url(url: str) -> str:
    """
    Apply simple substring-based rules to assign a category.
    If no rules match, return 'other'.
    """
    parsed = urlparse(url)
    path = parsed.path.lower()
    netloc = parsed.netloc.lower()
    full = (netloc + path).lower()

    # First, rules that care about netloc (subdomains / tools)
    # We can extend this if we find special subdomains like 'library.mdc.edu'
    for category, patterns in CATEGORY_RULES:
        for pattern in patterns:
            if pattern in full:
                return category

    return "other"


def main():
    urls = load_urls(INPUT_CLEAN_PATH)
    print(f"Loaded {len(urls)} cleaned URLs from {INPUT_CLEAN_PATH}")

    os.makedirs(os.path.dirname(OUTPUT_CSV_PATH), exist_ok=True)

    category_counts = {}
    target_urls = []

    with open(OUTPUT_CSV_PATH, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["url", "category"])

        for url in urls:
            category = categorize_url(url)
            writer.writerow([url, category])

            category_counts[category] = category_counts.get(category, 0) + 1

            if category in TARGET_CATEGORIES:
                target_urls.append(url)

    # Write target links for first scraping pass
    with open(OUTPUT_TARGET_PATH, "w", encoding="utf-8") as f:
        for url in target_urls:
            f.write(url + "\n")

    # Print summary
    print("\nCategory counts:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat:15s} {count}")

    print(f"\nSaved categorized URLs to: {OUTPUT_CSV_PATH}")
    print(f"Saved first-pass target URLs ({len(target_urls)} urls) to: {OUTPUT_TARGET_PATH}")


if __name__ == "__main__":
    main()
