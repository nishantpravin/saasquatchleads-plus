import os
import asyncio
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from core.scrape import fetch_site_bundle
from core.parse import extract_people_and_emails
from core.enrich import enrich_company
from core.enrich_api import wappalyzer_enrich, firmographics_enrich
from core.email_utils import infer_patterns, generate_candidates, check_mx
from core.smtp_verify import verify_batch
from core.dedupe import dedupe_people
from core.score import score_leads
from core.crm import push_hubspot_contacts, push_salesforce_leads

load_dotenv()

st.set_page_config(page_title="SaaSquatchLeads+ — Pro", layout="wide")
st.title("SaaSquatchLeads+ — Verify • Enrich • Push")
st.caption("Enrichment (Wappalyzer/Firmographics), NER roles, rate-limited SMTP verify (with consent), CRM push (HubSpot/Salesforce).")

with st.expander("New capabilities"):
    st.markdown("""
- **NER roles (spaCy):** better name/role extraction from page text.  
- **Wappalyzer / Firmographics:** optional API enrich if keys set; fallback to local sniffing.  
- **SMTP verify (consent):** Non-delivery SMTP RCPT check, rate-limited.  
- **CRM push:** Send selected rows to HubSpot or Salesforce.
    """)

# Input
left, right = st.columns([3,2], gap="large")
with left:
    input_mode = st.radio("Input mode", ["Paste URLs", "Upload CSV (company,url)"], horizontal=True)
    domains = []
    if input_mode == "Paste URLs":
        urls_text = st.text_area("Enter one per line (https://...)", height=150, placeholder="https://example.com\nhttps://another.io")
        if urls_text.strip():
            domains = [u.strip() for u in urls_text.splitlines() if u.strip()]
    else:
        up = st.file_uploader("Upload CSV with columns: company,url", type=["csv"])
        if up is not None:
            df_in = pd.read_csv(up)
            if not {"company","url"}.issubset(df_in.columns):
                st.error("CSV must contain columns: company,url")
            else:
                domains = df_in["url"].dropna().astype(str).tolist()

with right:
    target_roles = st.multiselect(
        "Target roles for candidate email generation",
        ["CEO","Founder","Co-Founder","Head of Growth","Growth","Marketing","Demand Gen","Sales","CTO","Product"],
        default=["Head of Growth","Marketing","Demand Gen","Sales","Founder","CEO"]
    )
    do_wapp = st.checkbox("Use Wappalyzer API (if key present)", value=True)
    do_firmo = st.checkbox("Firmographics API (if configured)", value=False)

    st.markdown("---")
    st.subheader("SMTP Verify (consent required)")
    consent = st.checkbox("I have legal consent to verify emails for these domains.", value=False)
    smtp_rate = st.slider("Max verifications per minute", 5, 120, 30)
    smtp_from = st.text_input("MAIL FROM address used in SMTP handshake", os.getenv("SMTP_FROM","noreply@example.com"))

    st.markdown("---")
    st.subheader("CRM Push")
    push_hubspot = st.checkbox("Enable HubSpot push (HUBSPOT_ACCESS_TOKEN)", value=False)
    push_salesf = st.checkbox("Enable Salesforce push (SF_* creds)", value=False)

run = st.button("Run Enrich (+ optional SMTP)", type="primary", use_container_width=True)

if run and domains:
    rows = []
    for url in domains:
        bundle = fetch_site_bundle(url)

        # Enrich (local)
        company = enrich_company(bundle)

        # Optional Wappalyzer/Firmographics
        wapp_data, w_status = (None, "skip")
        if do_wapp:
            wapp_data, w_status = wappalyzer_enrich(bundle.get("base_url"))
        firmo, f_status = (None, "skip")
        if do_firmo and company.get("domain"):
            firmo, f_status = firmographics_enrich(company.get("domain"))

        # Parse people/emails using enhanced NER+heuristics
        found_people, found_emails = extract_people_and_emails(bundle)

        # Pattern inference & candidates
        pattern_info = infer_patterns(found_emails, company.get("domain"))

        candidates = []
        for p in found_people:
            if any(r.lower() in (p.get("role","").lower()) for r in [r.lower() for r in target_roles]):
                candidates.extend(generate_candidates(p, company.get("domain"), pattern_info))

        # MX (cheap)
        mx_ok = check_mx(company.get("domain"))

        # Combine + dedupe
        all_people = found_people + candidates
        all_people = dedupe_people(all_people)

        # Score
        scored = score_leads(all_people, mx_ok=mx_ok, signals=company, pattern=pattern_info)

        for s in scored:
            s["company_name"] = company.get("name")
            s["company_domain"] = company.get("domain")
            techs = company.get("tech_stack", [])[:6]
            s["tech_summary"] = ", ".join(techs)
            s["mx_ok"] = mx_ok
            s["pattern"] = pattern_info.get("best_pattern")
            s["wappalyzer_status"] = w_status
            s["firmographics_status"] = f_status
            if firmo:
                s["firmo_size"] = firmo.get("size")
                s["firmo_employees"] = firmo.get("employees")
                s["firmo_founded_year"] = firmo.get("founded_year")
                s["firmo_hq_country"] = firmo.get("hq_country")
                s["firmo_linkedin"] = firmo.get("linkedin")
            rows.append(s)

    if rows:
        out = pd.DataFrame(rows)
        st.success(f"Done. {len(out)} leads enriched.")
        st.dataframe(out, use_container_width=True, height=440)

        csv = out.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", data=csv, file_name="leads_enriched.csv", mime="text/csv", use_container_width=True)

        # Optional SMTP verify (consent gate)
        if consent and smtp_from and len(out):
            st.info("SMTP verify running… (rate-limited)")
            emails = [e for e in out["email"].dropna().unique().tolist() if "@" in e]
            # Adjust rate dynamically
            from core import smtp_verify as sv
            sv.PER_MINUTE = smtp_rate  # set global limit used by decorator
            results = asyncio.run(verify_batch(emails, mail_from=smtp_from, per_minute=smtp_rate))
            out["smtp_verified"] = out["email"].map(results).fillna(False)
            st.dataframe(out, use_container_width=True, height=440)
            csv2 = out.to_csv(index=False).encode("utf-8")
            st.download_button("Download CSV + SMTP", data=csv2, file_name="leads_enriched_smtp.csv", mime="text/csv", use_container_width=True)
        elif not consent:
            st.warning("SMTP verification is disabled: consent not provided.")

        # CRM push
        st.markdown("### Push to CRM")
        sel = st.multiselect("Select rows to push", list(range(len(out))), format_func=lambda i: f"{out.iloc[i]['name']} — {out.iloc[i]['email']}", max_selections=100)
        if st.button("Push Selected"):
            push_rows = out.iloc[sel].to_dict("records") if sel else []
            if push_hubspot:
                res_h = push_hubspot_contacts(push_rows)
                if res_h.get("ok"):
                    st.success(f"HubSpot: pushed {res_h.get('count',0)} contacts.")
                else:
                    st.error(f"HubSpot push failed: {res_h}")
            if push_salesf:
                res_s = push_salesforce_leads(push_rows)
                if res_s.get("ok"):
                    st.success(f"Salesforce: created {res_s.get('created',0)} leads.")
                else:
                    st.error(f"Salesforce push failed: {res_s}")

    else:
        st.warning("No leads found. Try different sites or broaden target roles.")
elif run:
    st.warning("Please add at least one URL.")

st.caption("Tip: For NER, run `python -m spacy download en_core_web_sm`. Optional APIs are toggled and key-guarded.")
