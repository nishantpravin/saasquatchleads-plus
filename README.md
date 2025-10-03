# SaaSquatchLeads+ — Verify & Enrich (5-hour Feature)

**Goal:** Add a high-impact, low-friction module to SaaSquatchLeads that turns raw site inputs into **clean, enriched, de-duplicated leads** with **email pattern guesses** and **MX deliverability sanity**, then **scores and exports** them for immediate CRM use.

## Why this matters
Sales teams spend time cleaning data and chasing bad emails. This add-on:
- Extracts people/roles from public pages (About/Team/Contact),
- Infers email pattern from known emails (if any),
- Generates candidate emails for **growth/marketing/sales/founders**, 
- Validates domain MX (deliverability sanity),
- De-duplicates and **scores** leads, 
- Exports as CSV for CRM upload.

## Features
- Paste URLs or upload CSV (`company,url`)
- One-click **Enrich & Verify**
- **Email pattern inference** → candidate generation
- **MX record** check (fast)
- **Lead scoring** from signals & role
- **CSV export** (Salesforce/HubSpot ready)

## Setup
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Usage
1. Paste site URLs (or upload CSV with company,url)
2. Choose target roles (default focuses on Growth/Marketing/Sales + Founders/CEO)
3. Click Run Enrich & Verify
4. Review the table → Download CSV

## Notes & Ethics
- Uses only public pages/light parsing. No login bypassing or CAPTCHA evasion.
- MX check is a cheap deliverability sanity step, not a guarantee.

## Production hardening ideas
- robots.txt respect, concurrency limits, caching, optional SMTP handshake with consent, role NER.

## Next Steps (Stretch)
- SMTP verification with rate-limit/consent
- Wappalyzer/firmographics API enrichment
- HubSpot/Salesforce push
- spaCy/NER-based robust role detection
