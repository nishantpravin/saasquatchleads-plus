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

## Pro Features (Stretch)
- **spaCy NER roles** for robust name/role extraction.  
- **Wappalyzer API** enrichment (if `WAPPALYZER_API_KEY` set).  
- **Firmographics** API hook (set `FIRMO_API_URL`, `FIRMO_API_KEY`).  
- **SMTP verification** (rate-limited RCPT check; requires consent).  
- **CRM push** — HubSpot (Private App token) & Salesforce (username/password/token).

## Setup (Pro)
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
cp .env.example .env  # fill keys/tokens if you want API/CRM/SMTP features
streamlit run app.py
```

## SMTP Verification (Ethics & Ops)
Consent required: enable only if you have legal basis to verify.

Uses MX lookup + EHLO, MAIL FROM, RCPT TO (no DATA).

Rate-limited (default 30/min) with retries. Some servers will not respond reliably.

## CRM Push
HubSpot: set HUBSPOT_ACCESS_TOKEN (Private App). The app batches contacts create with basic properties.

Salesforce: set SF_USERNAME, SF_PASSWORD, SF_SECURITY_TOKEN, SF_DOMAIN. Creates Leads with minimal fields.

## Wappalyzer & Firmographics
Provide WAPPALYZER_API_KEY to call Wappalyzer API; otherwise the app falls back to local tech sniffing.

Provide FIRMO_API_URL & FIRMO_API_KEY for your in-house/company enrichment service.
