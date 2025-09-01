#!/usr/bin/env python3
"""
Enhanced Website Widget Scanner for Medical Practices with Practice Name Extraction.

This script scans medical practice websites to detect:
- Practice names from titles, headings, and meta tags
- Widgets and technologies used (booking systems, reviews, etc.)
- Creates a comprehensive leads CSV with Name, Website, Widgets columns

Usage:
1) Put practice URLs into a text file "urls.txt", one URL per line.
2) pip install requests beautifulsoup4 pandas lxml
3) python enhanced_leads_scraper.py

Outputs:
- enhanced_leads.csv          Main output with Name, Website, Widgets columns
- practice_details.csv        Detailed findings per practice
- widgets_summary.csv         Summary of all widgets found
"""

import re
import csv
import time
import json
import html
import hashlib
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import urllib3

# Suppress SSL warnings when verify=False is used
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URLS_FILE = "/Users/franziskaharzheim/Desktop/Lead Enricher/kfo-leads/urls.txt"
ENHANCED_LEADS_CSV = "enhanced_leads.csv"
PRACTICE_DETAILS_CSV = "practice_details.csv"
WIDGETS_SUMMARY_CSV = "widgets_summary.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
}

TIMEOUT = 20
SLEEP_BETWEEN_REQUESTS = 0.5

# Doctor relevant vendors, extended
VENDORS_DETECT = {
    "jameda":   re.compile(r"jameda\.(de|com)|widgets?\.jameda\.", re.I),
    "doctolib": re.compile(r"doctolib\.(de|fr|it)|community\.doctolib\.", re.I),
    "dr-flex":  re.compile(r"dr-?flex\.(de|com)|widget\.dr-?flex\.", re.I),
    "samedi":   re.compile(r"samedi\.(de|com)|widget\.samedi\.", re.I),
    "timify":   re.compile(r"timify\.(com|app)|terminapp|widget\.timify", re.I),
    "clickdoc": re.compile(r"(clickdoc|cgm)\.(de|com)|clickdoc-widget", re.I),
    "doctena":  re.compile(r"doctena\.(de|com|lu|be|nl)|booking\.doctena", re.I),
    "termed":   re.compile(r"(termed|terminmed)\.(de|com)", re.I),
    "medondo":  re.compile(r"medondo\.(de|com)|portal\.medondo", re.I),
    "etermin":  re.compile(r"etermin\.(ch|de|at)|\$eTermio|eTermio", re.I),
    # Telemedicine
    "sprechstunde-online": re.compile(r"sprechstunde\.online|zava\.(de|com)", re.I),
    "arztkonsultation": re.compile(r"arztkonsultation\.de", re.I),
    "cgm-video": re.compile(r"cgm.*video.*sprechstunde|video\.clickdoc", re.I),
    # Anamnesis and forms
    "idana": re.compile(r"idana\.(de|app)|app\.idana", re.I),
    "x-patient": re.compile(r"x\.patient|xpatient", re.I),
    "xonvid": re.compile(r"x\.onvid|onvid", re.I),
    # Prescriptions and orders
    "teleclinic": re.compile(r"teleclinic\.(de|com)", re.I),
    "gesund-de": re.compile(r"gesund\.de", re.I),
    "order-med": re.compile(r"order\.med|order-med", re.I),
    # Reviews
    "google-reviews": re.compile(r"google\.[a-z.]+/maps|g\.page|placeid", re.I),
    "provenexpert": re.compile(r"provenexpert\.com", re.I),
    # Payments (generic)
    "stripe": re.compile(r"checkout\.stripe|js\.stripe\.com", re.I),
    "paypal": re.compile(r"paypal\.com|paypalobjects\.com", re.I),
    # Additional common widgets
    "google-analytics": re.compile(r"google-analytics|gtag|ga\(|googletagmanager", re.I),
    "facebook-pixel": re.compile(r"facebook\.com/tr|fbq\(|fbevents", re.I),
    "mailchimp": re.compile(r"mailchimp|chimpstatic", re.I),
    "calendly": re.compile(r"calendly\.com", re.I),
    "typeform": re.compile(r"typeform\.com", re.I),
    "hubspot": re.compile(r"hubspot|hs-", re.I),
    "zendesk": re.compile(r"zendesk\.com", re.I),
    "intercom": re.compile(r"intercom\.io", re.I),
    "livechat": re.compile(r"livechatinc\.com", re.I),
    "tawk": re.compile(r"tawk\.to", re.I),
    "crisp": re.compile(r"crisp\.chat", re.I),
}

# Optional map for pretty naming and category export
VENDOR_META = {
    "jameda":   {"vendor_name": "Jameda", "hersteller": "jameda GmbH", "kategorie": "Bewertungen/Termin"},
    "doctolib": {"vendor_name": "Doctolib", "hersteller": "Doctolib GmbH", "kategorie": "Terminbuchung"},
    "dr-flex":  {"vendor_name": "Dr. Flex", "hersteller": "Dr. Flex GmbH", "kategorie": "Terminbuchung"},
    "samedi":   {"vendor_name": "samedi", "hersteller": "samedi GmbH", "kategorie": "Terminbuchung"},
    "timify":   {"vendor_name": "TIMIFY", "hersteller": "TerminApp GmbH", "kategorie": "Terminbuchung"},
    "clickdoc": {"vendor_name": "CLICKDOC", "hersteller": "CompuGroup Medical", "kategorie": "Terminbuchung/Video"},
    "doctena":  {"vendor_name": "Doctena", "hersteller": "Doctena", "kategorie": "Terminbuchung"},
    "termed":   {"vendor_name": "TerMed", "hersteller": "TerMed", "kategorie": "Terminbuchung/Video"},
    "medondo":  {"vendor_name": "Medondo", "hersteller": "Medondo GmbH", "kategorie": "Terminbuchung"},
    "etermin":  {"vendor_name": "eTermin", "hersteller": "eTermin AG", "kategorie": "Terminbuchung"},
    "sprechstunde-online": {"vendor_name": "sprechstunde.online", "hersteller": "Zava", "kategorie": "Telemedizin"},
    "arztkonsultation": {"vendor_name": "arztkonsultation.de", "hersteller": "arztkonsultation GmbH", "kategorie": "Telemedizin"},
    "cgm-video": {"vendor_name": "CGM Video Sprechstunde", "hersteller": "CompuGroup Medical", "kategorie": "Telemedizin"},
    "idana": {"vendor_name": "Idana", "hersteller": "idana GmbH", "kategorie": "Digitale Anamnese"},
    "x-patient": {"vendor_name": "x.patient", "hersteller": "x-cardiac GmbH", "kategorie": "Digitale Anamnese/Portal"},
    "xonvid": {"vendor_name": "x.onvid", "hersteller": "x-cardiac GmbH", "kategorie": "Digitale Aufnahme"},
    "teleclinic": {"vendor_name": "TeleClinic", "hersteller": "TeleClinic GmbH", "kategorie": "E-Rezept/Telemedizin"},
    "gesund-de": {"vendor_name": "gesund.de", "hersteller": "gesund.de GmbH", "kategorie": "E-Rezept/Apotheke"},
    "order-med": {"vendor_name": "order.med", "hersteller": "n/a", "kategorie": "Rezepte online"},
    "google-reviews": {"vendor_name": "Google Reviews", "hersteller": "Google LLC", "kategorie": "Bewertungen"},
    "provenexpert": {"vendor_name": "ProvenExpert", "hersteller": "Expert Systems AG", "kategorie": "Bewertungen"},
    "stripe": {"vendor_name": "Stripe", "hersteller": "Stripe Inc.", "kategorie": "Zahlung"},
    "paypal": {"vendor_name": "PayPal", "hersteller": "PayPal", "kategorie": "Zahlung"},
    "google-analytics": {"vendor_name": "Google Analytics", "hersteller": "Google LLC", "kategorie": "Web Analytics"},
    "facebook-pixel": {"vendor_name": "Facebook Pixel", "hersteller": "Meta", "kategorie": "Tracking"},
    "mailchimp": {"vendor_name": "Mailchimp", "hersteller": "Mailchimp", "kategorie": "Email Marketing"},
    "calendly": {"vendor_name": "Calendly", "hersteller": "Calendly", "kategorie": "Terminbuchung"},
    "typeform": {"vendor_name": "Typeform", "hersteller": "Typeform", "kategorie": "Formulare"},
    "hubspot": {"vendor_name": "HubSpot", "hersteller": "HubSpot", "kategorie": "CRM/Marketing"},
    "zendesk": {"vendor_name": "Zendesk", "hersteller": "Zendesk", "kategorie": "Support"},
    "intercom": {"vendor_name": "Intercom", "hersteller": "Intercom", "kategorie": "Chat/Support"},
    "livechat": {"vendor_name": "LiveChat", "hersteller": "LiveChat", "kategorie": "Chat"},
    "tawk": {"vendor_name": "Tawk.to", "hersteller": "Tawk.to", "kategorie": "Chat"},
    "crisp": {"vendor_name": "Crisp", "hersteller": "Crisp", "kategorie": "Chat"},
}

IFRAME_ATTRS = ["src", "data-src", "data-url"]
A_ATTRS = ["href", "data-href"]
SCRIPT_ATTRS = ["src"]

JS_HINTS = [
    re.compile(r"\$eTermio|eTermio|Doctolib|DrFlex|samedi|Doctena|Clickdoc|Timify|Idana", re.I),
    re.compile(r"window\.open\(['\"](.*?)['\"]", re.I),
    re.compile(r"location\.href\s*=\s*['\"](.*?)['\"]", re.I),
    re.compile(r"data-url\s*=\s*['\"](.*?)['\"]", re.I),
]

META_REFRESH_RE = re.compile(r'url=([^;]+)', re.I)

def absolute_url(base, url):
    if not url:
        return None
    return urljoin(base, url)

def fetch(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True, verify=False)
        final_url = resp.url
        history = [r.status_code for r in resp.history] + [resp.status_code]
        return resp, final_url, history
    except requests.RequestException as e:
        return None, None, [str(e)]

def extract_practice_name(soup, url):
    """Extract practice name from various sources on the webpage"""
    practice_name = ""
    
    # Try title tag first
    title = soup.find("title")
    if title and title.string:
        title_text = title.string.strip()
        # Clean up common title patterns
        title_text = re.sub(r'\s*[-|]\s*.*$', '', title_text)  # Remove everything after dash/pipe
        title_text = re.sub(r'\s*\|.*$', '', title_text)  # Remove everything after pipe
        if title_text and len(title_text) > 3:
            practice_name = title_text
    
    # Try h1 tags
    if not practice_name:
        h1_tags = soup.find_all("h1")
        for h1 in h1_tags:
            h1_text = h1.get_text(strip=True)
            if h1_text and len(h1_text) > 3 and len(h1_text) < 100:
                practice_name = h1_text
                break
    
    # Try meta description
    if not practice_name:
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            desc = meta_desc.get("content").strip()
            if desc and len(desc) > 3:
                practice_name = desc[:50]  # Take first 50 chars
    
    # Try to extract from URL if no name found
    if not practice_name:
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith("www."):
            domain = domain[4:]
        practice_name = domain.replace("-", " ").replace(".", " ").title()
    
    return practice_name

def extract_meta_refresh(soup):
    meta = soup.find("meta", attrs={"http-equiv": re.compile(r"refresh", re.I)})
    if not meta:
        return None
    content = meta.get("content", "")
    m = META_REFRESH_RE.search(content or "")
    if m:
        return m.group(1).strip()
    return None

def scan_page(url):
    """Scan a single page for widgets and extract practice information"""
    practice_info = {
        "url": url,
        "practice_name": "",
        "widgets_found": set(),
        "widget_details": [],
        "final_url": "",
        "http_status": "",
        "error": None
    }
    
    resp, final_url, history = fetch(url)
    if not resp or not resp.text:
        practice_info["error"] = f"Failed to fetch: {history}"
        return practice_info
    
    practice_info["final_url"] = final_url
    practice_info["http_status"] = history[-1] if history else "unknown"
    
    html_text = resp.text
    soup = BeautifulSoup(html_text, "lxml")
    
    # Extract practice name
    practice_info["practice_name"] = extract_practice_name(soup, url)
    
    # Meta refresh detection
    meta_url = extract_meta_refresh(soup)
    if meta_url:
        meta_abs = absolute_url(final_url, meta_url)
        vendor_key = detect_vendor(meta_abs or meta_url)
        if vendor_key:
            practice_info["widgets_found"].add(vendor_key)
            practice_info["widget_details"].append({
                "type": "meta-refresh",
                "vendor": vendor_key,
                "vendor_name": pretty_vendor(vendor_key),
                "value": meta_abs or meta_url
            })

    # iFrames
    for iframe in soup.find_all("iframe"):
        for attr in IFRAME_ATTRS:
            v = iframe.get(attr)
            if not v:
                continue
            val = absolute_url(final_url, v)
            vendor_key = detect_vendor(val or v)
            if vendor_key:
                practice_info["widgets_found"].add(vendor_key)
                practice_info["widget_details"].append({
                    "type": "iframe",
                    "vendor": vendor_key,
                    "vendor_name": pretty_vendor(vendor_key),
                    "value": val or v
                })

    # Links and buttons
    for a in soup.find_all("a"):
        for attr in A_ATTRS:
            v = a.get(attr)
            if not v:
                continue
            val = absolute_url(final_url, v)
            text = " ".join(a.get_text(strip=True).split())
            vendor_key = detect_vendor(val or v) or detect_vendor(text)
            if vendor_key:
                practice_info["widgets_found"].add(vendor_key)
                practice_info["widget_details"].append({
                    "type": "link",
                    "vendor": vendor_key,
                    "vendor_name": pretty_vendor(vendor_key),
                    "value": val or v,
                    "text": text
                })

    # Scripts src
    for s in soup.find_all("script"):
        for attr in SCRIPT_ATTRS:
            v = s.get(attr)
            if not v:
                continue
            val = absolute_url(final_url, v)
            vendor_key = detect_vendor(val or v)
            if vendor_key:
                practice_info["widgets_found"].add(vendor_key)
                practice_info["widget_details"].append({
                    "type": "script",
                    "vendor": vendor_key,
                    "vendor_name": pretty_vendor(vendor_key),
                    "value": val or v
                })

        # Inline JS hints
        if not s.get("src") and s.string:
            s_text = s.string
            for hint in JS_HINTS:
                for m in hint.finditer(s_text):
                    target = m.group(1) if m.groups() else s_text[:80]
                    vendor_key = detect_vendor(target) or detect_vendor(s_text)
                    if vendor_key:
                        practice_info["widgets_found"].add(vendor_key)
                        practice_info["widget_details"].append({
                            "type": "inline-js",
                            "vendor": vendor_key,
                            "vendor_name": pretty_vendor(vendor_key),
                            "value": target
                        })

    return practice_info

def detect_vendor(value):
    if not value:
        return None
    try:
        val = value if isinstance(value, str) else str(value)
    except Exception:
        val = str(value)
    for key, rx in VENDORS_DETECT.items():
        if rx.search(val):
            return key
    return None

def pretty_vendor(vendor_key):
    if not vendor_key:
        return ""
    meta = VENDOR_META.get(vendor_key)
    if not meta:
        return vendor_key
    return f"{meta['vendor_name']} ({meta['kategorie']})"

def load_urls(path):
    urls = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            u = line.strip()
            if not u:
                continue
            if not urlparse(u).scheme:
                u = "http://" + u
            urls.append(u)
    return urls

def save_enhanced_leads(practices, path):
    """Save the main enhanced leads CSV with Name, Website, Widgets columns"""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Website", "Widgets"])
        
        for practice in practices:
            if practice["error"]:
                widgets = "Error: " + practice["error"]
            else:
                widgets = "; ".join([pretty_vendor(w) for w in practice["widgets_found"]]) if practice["widgets_found"] else "None detected"
            
            writer.writerow([
                practice["practice_name"],
                practice["url"],
                widgets
            ])

def save_practice_details(practices, path):
    """Save detailed findings for each practice"""
    if not practices:
        return
    
    # Get all possible fields
    all_fields = set()
    for practice in practices:
        all_fields.update(practice.keys())
    
    fieldnames = ["url", "practice_name", "final_url", "http_status", "error", "widgets_found", "widget_details"]
    
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for practice in practices:
            # Convert sets to strings for CSV
            practice_copy = practice.copy()
            practice_copy["widgets_found"] = "; ".join(practice["widgets_found"]) if practice["widgets_found"] else ""
            practice_copy["widget_details"] = json.dumps(practice["widget_details"], ensure_ascii=False)
            writer.writerow(practice_copy)

def save_widgets_summary(practices, path):
    """Save a summary of all widgets found across all practices"""
    widget_counts = {}
    widget_practices = {}
    
    for practice in practices:
        if practice["error"]:
            continue
        
        for widget in practice["widgets_found"]:
            if widget not in widget_counts:
                widget_counts[widget] = 0
                widget_practices[widget] = []
            
            widget_counts[widget] += 1
            widget_practices[widget].append(practice["practice_name"])
    
    # Sort by count descending
    sorted_widgets = sorted(widget_counts.items(), key=lambda x: x[1], reverse=True)
    
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Widget", "Count", "Vendor Name", "Category", "Practices Using"])
        
        for widget, count in sorted_widgets:
            meta = VENDOR_META.get(widget, {})
            vendor_name = meta.get("vendor_name", widget)
            category = meta.get("kategorie", "")
            practices_list = "; ".join(widget_practices[widget])
            
            writer.writerow([widget, count, vendor_name, category, practices_list])

def main():
    try:
        urls = load_urls(URLS_FILE)
    except FileNotFoundError:
        print(f"Missing {URLS_FILE}. Create it with one URL per line.")
        return

    print(f"Starting scan of {len(urls)} practice websites...")
    
    practices = []
    for idx, url in enumerate(urls, 1):
        print(f"[{idx}/{len(urls)}] Scanning {url}")
        practice_info = scan_page(url)
        practices.append(practice_info)
        time.sleep(SLEEP_BETWEEN_REQUESTS)

    if not practices:
        print("No results found.")
        return

    # Save enhanced leads (main output)
    save_enhanced_leads(practices, ENHANCED_LEADS_CSV)
    print(f"Saved enhanced leads to {ENHANCED_LEADS_CSV}")

    # Save detailed practice information
    save_practice_details(practices, PRACTICE_DETAILS_CSV)
    print(f"Saved practice details to {PRACTICE_DETAILS_CSV}")

    # Save widgets summary
    save_widgets_summary(practices, WIDGETS_SUMMARY_CSV)
    print(f"Saved widgets summary to {WIDGETS_SUMMARY_CSV}")

    # Print summary
    successful_scans = len([p for p in practices if not p["error"]])
    total_widgets = sum(len(p["widgets_found"]) for p in practices if not p["error"])
    
    print(f"\nScan completed!")
    print(f"Successfully scanned: {successful_scans}/{len(urls)} practices")
    print(f"Total widgets detected: {total_widgets}")
    
    if successful_scans > 0:
        avg_widgets = total_widgets / successful_scans
        print(f"Average widgets per practice: {avg_widgets:.1f}")

if __name__ == "__main__":
    main()
