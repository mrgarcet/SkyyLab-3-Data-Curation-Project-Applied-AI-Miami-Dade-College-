#!/usr/bin/env python3
"""
url_categorizer.py (v0.2.2)

- HTML:
  Input : ../data/html_links_v3.txt
  Output: ../data/urls_with_category_v3.csv (url, category, confidence, reason)
          ../data/target_links_v3.txt      (subset for MVP scraping; HTML only)

- PDF (optional):
  Input : ../data/pdf_links_v3.txt   # override with --pdf
  Output: ../data/pdfs_with_category_v3.csv
          # optional: --pdf-out-txt ../data/target_pdfs_v3.txt

Run AFTER link_cleaner.py and BEFORE page_scraper.py.
"""

from __future__ import annotations
import argparse
import csv
import os
import re
from urllib.parse import urlparse

# ---------- CLI defaults ----------
DEFAULT_INPUT       = "../data/html_links_v3.txt"
DEFAULT_OUT_CSV     = "../data/urls_with_category_v3.csv"
DEFAULT_OUT_TXT     = "../data/target_links_v3.txt"

DEFAULT_PDF_INPUT   = "../data/pdf_links_v3.txt"   # if missing, PDFs are skipped
DEFAULT_PDF_OUT_CSV = "../data/pdfs_with_category_v3.csv"

# ---------- Categories ----------
MVP_CATEGORIES = {
    "Admissions & Getting Started",
    "Advising & Registration",
    "Testing & Placement",
    "Costs & Payments",
    "Financial Aid & Scholarships",
    "Programs, Degrees & Catalog",
    "Student Resources & Support",
    "Library & Research",
    "Career Services (MDC WORKS)",
    "Continuing Education (non-credit)",
    "MDC Online",
    "International Students",
    "Veterans & Military",
    "Campuses & Locations",
}

NON_MVP = {
    "News & Press",
    "Events & Calendar",
    "Foundation & Alumni",
    "Policies & Procedures",
    "Public Safety & Emergency",
    "Portals & Systems",
    "Other/Uncategorized",
}

# ---------- Host rules (score, reason) ----------
HOST_RULES: list[tuple[re.Pattern, tuple[str, float, str]]] = [
    (re.compile(r"^calendar\.mdc\.edu$"),                ("Events & Calendar", 1.0, "host:calendar")),
    (re.compile(r"^eventhub\.sharkevents\.mdc\.edu$"),   ("Events & Calendar", 1.0, "host:eventhub")),
    (re.compile(r"^news\.mdc\.edu$"),                    ("News & Press", 1.0, "host:news")),
    (re.compile(r"^libraryguides\.mdc\.edu$"),           ("Library & Research", 1.0, "host:libraryguides")),
    (re.compile(r"^faq\.mdc\.edu$"),                     ("Student Resources & Support", 0.95, "host:faq")),
    (re.compile(r"^ce\.mdc\.edu$"),                      ("Continuing Education (non-credit)", 1.0, "host:ce")),
    (re.compile(r"^online\.mdc\.edu$"),                  ("MDC Online", 1.0, "host:online")),
    (re.compile(r"^foundation\.mdc\.edu$"),              ("Foundation & Alumni", 1.0, "host:foundation")),
    (re.compile(r"^mdconnect\.mdc\.edu$"),               ("Portals & Systems", 1.0, "host:mdconnect")),
    (re.compile(r"^findclasses\.mdc\.edu$"),             ("Portals & Systems", 1.0, "host:findclasses")),
    (re.compile(r"^cs\.mdc\.edu$"),                      ("Portals & Systems", 1.0, "host:cs")),
    (re.compile(r"^my\.mdc\.edu$"),                      ("Portals & Systems", 1.0, "host:my")),
    (re.compile(r"^(mycourses|myoffice)\.mdc\.edu$"),    ("Portals & Systems", 1.0, "host:lms/office")),
    (re.compile(r"^(support|owa|adfs|sharknet)\.mdc\.edu$"), ("Portals & Systems", 1.0, "host:portal")),
    # Academic/Program subdomains -> Programs/Degrees
    (re.compile(r"^(entec|scet|magic|nwsa)\.mdc\.edu$"), ("Programs, Degrees & Catalog", 0.95, "host:academic-subdomain")),
]

# campus slugs
CAMPUS_SLUG = r"(hialeah|homestead|kendall|medical|north|padron|west|wolfson|meek|gibson)"

# Heuristic: many program pages are top-level slugs not under /academics/
PROGRAM_SLUG_RX = re.compile(
    r"^/(aviation|aviationmaintenance|flightinstructor|professionalpilot|commercialtransportpilot|"
    r"emt|ems|paramedic|firefighter|lawenforcementbrt|privateinvestigatorintern|criminaljustice(bs|technology)?|justice|"
    r"nursing|bsn|medical(laboratorysciences|technology)?|healthinformation|healthservicesas|histotechnology(bas)?|"
    r"steriletech|dental(-|)?hygiene|sonography|respiratorycare|surgicaltechnology|veterinarytechnology|opticianry|"
    r"pharmacytechnician|phlebotomy|ct|mri|massagetherapy|medicalcoderbiller|physicaltherapistassistant|"
    r"architecture(-interior-design)?|makerslab|magic|cloudcomputingcenter|bitcenter|cybersecurity(bs)?|softwareengineering|"
    r"dataanalytics|electronicsengineeringbs|information(systemsnetworking|systemsnetworking)?|computerinformationtechnology|"
    r"business(administration|administrationas)?|accountingmanagement|marketing|digitalmarketing(bas)?|"
    r"supplychain(management|analytics)|procurement-management|project-management|entrepreneurship|psychology|"
    r"education|scienceeducation|earlychildhood.*|secondary(math|biology)|readingendorsement|biotechnology|biopharmaceutical|"
    r"culinary|hospitality(-institute|management)?|fashion|taxspecialist|neuroscience"
    r")(/|$)",
    re.I,
)

PATH_RULES: list[tuple[re.Pattern, tuple[str, float, str]]] = [
    # Campuses
    (re.compile(rf"^/{CAMPUS_SLUG}(/|$)"),                ("Campuses & Locations", 0.95, "path:campus")),
    (re.compile(r"^/(campus|campus-finder)(/|$)"),        ("Campuses & Locations", 0.9, "path:campusfinder")),

    # Admissions & Getting Started
    (re.compile(r"^/(future-students|admissions|admissions-info|apply|orientation)(/|$)"),
     ("Admissions & Getting Started", 0.9, "path:admissions")),

    # Advising & Registration
    (re.compile(r"^/(advisement|registration|navigate|transcripts|registrar|enroll|enrollment-verification)(/|$)"),
     ("Advising & Registration", 0.9, "path:advising")),

    # Testing & Placement
    (re.compile(r"^/(testing|aet|fcle|testing-criteria|testing/tests)(/|$)"),
     ("Testing & Placement", 0.9, "path:testing")),

    # Costs & Payments
    (re.compile(r"^/(student-financial-services|tuition|costs|payment-options|due-dates|refunds|wiretransfer|mdcconnect-update)(/|$)"),
     ("Costs & Payments", 0.92, "path:costs")),

    # Financial Aid & Scholarships
    (re.compile(r"^/(financialaid|scholarships|financialliteracy|workstudy)(/|$)"),
     ("Financial Aid & Scholarships", 0.92, "path:aid")),

    # Programs, Degrees & Catalog
    (re.compile(r"^/(academics|catalog|academics/programs|bachelors|associate|certificate|general-education|programs)(/|$)"),
     ("Programs, Degrees & Catalog", 0.92, "path:academics")),
    (PROGRAM_SLUG_RX,                                    ("Programs, Degrees & Catalog", 0.88, "path:program-slug")),

    # Library & Research
    (re.compile(r"^/(learning-resources|libraries|libraryforms)(/|$)"),
     ("Library & Research", 0.9, "path:library")),

    # Career Services
    (re.compile(r"^/mdcworks(/|$)"),                      ("Career Services (MDC WORKS)", 0.9, "path:mdcworks")),
    (re.compile(r"^/career-exploration(/|$)"),            ("Career Services (MDC WORKS)", 0.85, "path:career-exploration")),

    # Continuing Education
    (re.compile(r"^/ce(/|$)"),                            ("Continuing Education (non-credit)", 0.9, "path:ce")),

    # MDC Online
    (re.compile(r"^/online(/|$)"),                        ("MDC Online", 0.86, "path:online")),

    # Intl & Veterans
    (re.compile(r"^/internationalstudents(/|$)"),         ("International Students", 0.95, "path:intl")),
    (re.compile(r"^/veterans(/|$)"),                      ("Veterans & Military", 0.95, "path:vets")),

    # Student Resources & Support
    (re.compile(r"^/(studentlife|student-wellness|singlestop|access|bookstore|pantry|kendallfitness|northfitness|wolfsonfitness|racquet-sports)(/|$)"),
     ("Student Resources & Support", 0.9, "path:student-resources")),

    # Public Safety & Policies
    (re.compile(r"^/(safety|preventsexualviolence|main/safety)(/|$)"),
     ("Public Safety & Emergency", 0.85, "path:safety")),
    (re.compile(r"^/(policy|procedures|rightsandresponsibilities)(/|$)"),
     ("Policies & Procedures", 0.86, "path:policy")),

    # News/Events
    (re.compile(r"^/(collegeforum|news)(/|$)"),
     ("News & Press", 0.8, "path:news")),
    (re.compile(r"^/livestream(/|$)"),
     ("Events & Calendar", 0.6, "path:livestream")),

    # Legacy /main structure (older site)
    (re.compile(r"^/main/(testing|assessments|pert|accuplacer)(/|$)"),
     ("Testing & Placement", 0.88, "path:main-testing")),
    (re.compile(r"^/main/financialaid(/|$)"),
     ("Financial Aid & Scholarships", 0.88, "path:main-financialaid")),
    (re.compile(r"^/main/safety(/|$)"),
     ("Public Safety & Emergency", 0.88, "path:main-safety")),
    (re.compile(r"^/main/library(/|$)"),
     ("Library & Research", 0.88, "path:main-library")),
    (re.compile(r"^/main/register(/|$)"),
     ("Advising & Registration", 0.88, "path:main-register")),
    (re.compile(r"^/main/bookstore(/|$)"),
     ("Student Resources & Support", 0.86, "path:main-bookstore")),
]

KEYWORD_HINTS: list[tuple[re.Pattern, tuple[str, float]]] = [
    (re.compile(r"financial\s+aid|fafsa|scholarship", re.I),             ("Financial Aid & Scholarships", 0.55)),
    (re.compile(r"tuition|fees|payment|refund|invoice", re.I),           ("Costs & Payments", 0.55)),
    (re.compile(r"advis(e|ing)|registration|enroll|navigate|transcript", re.I), ("Advising & Registration", 0.55)),
    (re.compile(r"test|placement|exam|clep|pert|fcle", re.I),            ("Testing & Placement", 0.55)),
    (re.compile(r"degree|program|certificate|catalog|curriculum", re.I), ("Programs, Degrees & Catalog", 0.55)),
    (re.compile(r"library|database|research|libguide", re.I),            ("Library & Research", 0.55)),
    (re.compile(r"hialeah|homestead|kendall|medical|north|padron|west|wolfson|meek|gibson", re.I),
     ("Campuses & Locations", 0.52)),
]

# PDF-only filename/path hints (extra signal)
PDF_HINTS: list[tuple[re.Pattern, tuple[str, float, str]]] = [
    (re.compile(r"catalog|course(\s|-|_)?descriptions?", re.I),     ("Programs, Degrees & Catalog", 0.75, "pdf:catalog")),
    (re.compile(r"policy|procedure|agreement|addendum", re.I),      ("Policies & Procedures", 0.7, "pdf:policy")),
    (re.compile(r"transcript|reverse[-_ ]?transfer|ferpa", re.I),   ("Advising & Registration", 0.65, "pdf:registrar")),
    (re.compile(r"scholarship|fafsa|financial[-_ ]?aid", re.I),     ("Financial Aid & Scholarships", 0.7, "pdf:aid")),
    (re.compile(r"tuition|fee(s)?|financial[-_ ]obligation", re.I), ("Costs & Payments", 0.7, "pdf:costs")),
    (re.compile(r"pert|clep|fcle|accuplacer|test(score|ing)?", re.I),("Testing & Placement", 0.7, "pdf:testing")),
    (re.compile(r"safety|emergency|crime|hazing", re.I),            ("Public Safety & Emergency", 0.65, "pdf:safety")),
    (re.compile(r"library|research|database", re.I),                 ("Library & Research", 0.6, "pdf:library")),
    # Media kits, “in the news”, clippings under news uploads
    (re.compile(r"/wp-content/uploads/", re.I),                      ("News & Press", 0.9, "pdf:news-uploads")),
]

def is_pdf_url(u: str) -> bool:
    return u.lower().endswith(".pdf")

def clean_url(u: str) -> str:
    return u.strip()

def score_candidates(url: str, is_pdf: bool):
    pu = urlparse(url)
    host = pu.netloc.lower()
    path = pu.path or "/"
    path_lower = path.lower()

    candidates: list[tuple[str, float, str]] = []

    # 1) Host rules
    for rx, (cat, score, reason) in HOST_RULES:
        if rx.match(host):
            candidates.append((cat, score, reason))

    # 2) Path rules (for mdc.edu main site & subdomains that use mdc IA)
    if host.endswith(".mdc.edu") or host in ("mdc.edu", "www.mdc.edu", "www3.mdc.edu"):
        for rx, (cat, score, reason) in PATH_RULES:
            if rx.match(path_lower):
                candidates.append((cat, score, reason))

    # 3) Keyword hints (low weight; last resort)
    for rx, (cat, score) in KEYWORD_HINTS:
        if rx.search(url):
            candidates.append((cat, score, f"kw:{rx.pattern[:20]}"))

    # 4) PDF-specific hints
    if is_pdf:
        # filename and full URL
        for rx, (cat, score, reason) in PDF_HINTS:
            if rx.search(url):
                candidates.append((cat, score, reason))

    return candidates

def choose_best(candidates: list[tuple[str, float, str]]):
    if not candidates:
        return ("Other/Uncategorized", 0.0, "no-rule")

    # pick highest score; tie-break: prefer MVP categories
    candidates.sort(key=lambda t: t[1], reverse=True)
    top_score = candidates[0][1]
    top = [c for c in candidates if abs(c[1] - top_score) < 1e-9]

    # prefer MVP among ties
    for cat, score, reason in top:
        if cat in MVP_CATEGORIES:
            reasons = ";".join([r for (ct, sc, r) in candidates if ct == cat and abs(sc - top_score) < 1e-9])
            return (cat, score, reasons)

    # else first of top
    reasons = ";".join([r for (ct, sc, r) in candidates if ct == top[0][0] and abs(sc - top_score) < 1e-9])
    return (top[0][0], top_score, reasons)

def categorize(url: str):
    try:
        pdf = is_pdf_url(url)
        candidates = score_candidates(url, pdf)
        return choose_best(candidates)
    except Exception as e:
        return ("Other/Uncategorized", 0.0, f"error:{e}")

def run_one(input_path: str, out_csv: str, out_txt: str | None, html_only_targets: bool):
    if not os.path.exists(input_path):
        print(f"[skip] Input not found: {input_path}")
        return 0, {}

    with open(input_path, "r", encoding="utf-8") as f:
        urls = [clean_url(line) for line in f if line.strip()]

    rows = []
    target = []
    counts: dict[str, int] = {}

    for u in urls:
        cat, score, reason = categorize(u)
        rows.append((u, cat, f"{score:.2f}", reason))
        counts[cat] = counts.get(cat, 0) + 1
        # Only add to target if (a) MVP category and (b) we are writing HTML targets
        if out_txt and cat in MVP_CATEGORIES and html_only_targets and not is_pdf_url(u):
            target.append(u)

    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as out:
        w = csv.writer(out)
        w.writerow(["url", "category", "confidence", "reason"])
        w.writerows(rows)

    if out_txt:
        os.makedirs(os.path.dirname(out_txt), exist_ok=True)
        with open(out_txt, "w", encoding="utf-8") as out:
            for u in target:
                out.write(u + "\n")

    return len(urls), counts

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=DEFAULT_INPUT, help="HTML links file")
    ap.add_argument("--out-csv", default=DEFAULT_OUT_CSV)
    ap.add_argument("--out-txt", default=DEFAULT_OUT_TXT, help="MVP HTML targets (for page_scraper)")

    ap.add_argument("--pdf", default=DEFAULT_PDF_INPUT, help="PDF links file (optional)")
    ap.add_argument("--pdf-out-csv", default=DEFAULT_PDF_OUT_CSV)
    ap.add_argument("--pdf-out-txt", default=None, help="Optional MVP PDF targets (kept separate)")

    args = ap.parse_args()

    # HTML pass (writes target_links for page_scraper)
    n_html, counts_html = run_one(args.input, args.out_csv, args.out_txt, html_only_targets=True)

    # PDF pass (separate CSV; targets optional and separate)
    n_pdf, counts_pdf = 0, {}
    if args.pdf and os.path.exists(args.pdf):
        n_pdf, counts_pdf = run_one(args.pdf, args.pdf_out_csv, args.pdf_out_txt, html_only_targets=False)
    else:
        print(f"[info] PDF list not found or not provided: {args.pdf}")

    # Console summary
    if n_html:
        print("\nHTML category counts:")
        for k in sorted(counts_html, key=counts_html.get, reverse=True):
            print(f"  {k:30s} {counts_html[k]}")
        print(f"\nWrote: {args.out_csv}")
        if args.out_txt:
            print(f"Wrote: {args.out_txt}  (MVP categories only; HTML only)")

    if n_pdf:
        print("\nPDF category counts:")
        for k in sorted(counts_pdf, key=counts_pdf.get, reverse=True):
            print(f"  {k:30s} {counts_pdf[k]}")
        print(f"\nWrote: {args.pdf_out_csv}")
        if args.pdf_out_txt:
            print(f"Wrote: {args.pdf_out_txt}  (MVP categories only; PDFs)")
    print("")

if __name__ == "__main__":
    main()
