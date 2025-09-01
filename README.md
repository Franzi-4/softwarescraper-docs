# Enhanced Website Widget Scanner for Medical Practices

Scan medical practice websites, extract the likely practice name, detect embedded widgets and services, and export clean lead files.

## What it does

- Finds a practice name from common places like `<title>`, `<h1>`, and meta description
- Detects booking, review, analytics, chat, and payment widgets through iframes, scripts, links, meta refresh, and inline JS hints
- Outputs three CSVs you can use in outreach and analysis

## Quick start

1) Put target URLs in a file named `urls.txt`, one URL per line.  
   You can use bare domains or full URLs.

https://www.praxis-meier.de
kieferorthopaedie-huber.de
https://www.zahnarzt-beispiel.at/team

2) Install dependencies:
```bash
pip install requests beautifulsoup4 pandas lxml

	3.	Adjust the path to your urls.txt if needed. In the script update:

URLS_FILE = "/Users/you/path/urls.txt"

or set it to "urls.txt" if the file is in the same folder.

	4.	Run:

python enhanced_leads_scraper.py



Outputs
	•	enhanced_leads.csv
Main sheet with one row per website.
	•	Name: extracted practice name
	•	Website: original URL from your input list
	•	Widgets: pretty printed list of detected vendors and categories or an error note
	•	practice_details.csv
Detailed JSON like evidence per practice.
	•	url, practice_name, final_url, http_status, error
	•	widgets_found: semicolon list of vendor keys
	•	widget_details: JSON array of matches with type, vendor, vendor_name, value, and optional text
	•	widgets_summary.csv
Cross site widget stats.
	•	Widget (vendor key), Count, Vendor Name, Category, Practices Using

Sample enhanced_leads.csv

Name	Website	Widgets
Praxis Dr Meier	https://www.praxis-meier.de	Doctolib (Terminbuchung); Google Reviews (Bewertungen)
Kieferorthopädie Huber	http://kieferorthopaedie-huber.de	Jameda (Bewertungen/Termin)
Zahnärzte am Park	https://zahnaerzte-park.at	None detected

Vendors detected

Booking and telemedicine: Doctolib, Dr Flex, samedi, TIMIFY, CLICKDOC, Doctena, TerMed, Medondo, eTermin, CGM Video, sprechstunde.online, arztkonsultation.de
Forms and anamnesis: Idana, x.patient, x.onvid, Typeform
Reviews: Google Reviews, ProvenExpert
Payments: Stripe, PayPal
Analytics and marketing: Google Analytics, Facebook Pixel, HubSpot, Mailchimp, Google Tag Manager
Chat and support: Zendesk, Intercom, LiveChat, Tawk.to, Crisp
Calendar: Calendly

Detection uses regex matches on iframes, links, script src, meta refresh, and inline JS hints.

How it works
	1.	Fetches each URL with a desktop browser User Agent
	2.	Follows redirects and records the final URL and status history
	3.	Parses HTML with lxml based BeautifulSoup
	4.	Extracts a practice name using a best effort order:
	•	<title> cleaned of separators
	•	<h1> candidates
	•	meta description first 50 characters
	•	domain fallback, for example zahnarzt-meier.de becomes Zahnarzt Meier
	5.	Scans DOM and inline JS for vendor patterns and collects evidence
	6.	Writes three CSVs and a short console summary

Configuration

Open the script and adjust these constants if needed:

URLS_FILE = "urls.txt"                    # input list
ENHANCED_LEADS_CSV = "enhanced_leads.csv"
PRACTICE_DETAILS_CSV = "practice_details.csv"
WIDGETS_SUMMARY_CSV = "widgets_summary.csv"

TIMEOUT = 20
SLEEP_BETWEEN_REQUESTS = 0.5

HEADERS = { ... }                         # default desktop UA

You can extend VENDORS_DETECT with new regexes and map them in VENDOR_META for nicer names and categories.

Tips
	•	Rate limiting: increase SLEEP_BETWEEN_REQUESTS for large lists
	•	Mixed pages: the scanner checks iframes, links, and scripts on the current page only. For deeper coverage, feed direct booking or contact pages into urls.txt as well
	•	Redirects: meta refresh targets are followed for detection and recorded as evidence
	•	Errors: sites that time out or block the request will appear with an Error: message in enhanced_leads.csv

Troubleshooting
	•	SSL warnings on some sites: the script sets verify=False and suppresses warnings. If you want strict TLS, set verify=True in requests.get
	•	Blocked by WAF or bot filters: try a different User Agent, add retries, or run through a consenting proxy where allowed
	•	Empty widgets: some vendors load content after user interaction. Server side parsing may miss those. Consider adding a headless browser if you need full client side execution

Ethics and legality

Only scan sites you are allowed to access. Respect robots.txt where applicable, terms of use, and privacy laws. Do not store personal data. This tool reads public HTML and reports aggregated widget presence.

Requirements
	•	Python 3.9 or newer
	•	requests, beautifulsoup4, lxml, pandas

Install:

pip install requests beautifulsoup4 pandas lxml

Run

python enhanced_leads_scraper.py

License

Add your preferred license. MIT is a common choice.

