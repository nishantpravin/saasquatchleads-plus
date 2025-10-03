import streamlit as st
import pandas as pd
from core.scrape import fetch_site_bundle
from core.parse import extract_people_and_emails
from core.enrich import enrich_company
from core.email_utils import infer_patterns, generate_candidates, check_mx
from core.dedupe import dedupe_people
from core.score import score_leads

st.set_page_config(page_title="SaaSquatchLeads+: Verify & Enrich", layout="wide")

st.title("SaaSquatchLeads+ — One-Click Verify & Enrich")
st.caption("Paste company homepages or upload a CSV with `company`,`url`. Get clean, de-duped, enriched leads + email guesses with MX checks.")

with st.expander("How it works"):
    st.write("""
1) Fetch homepage and common team/contact pages.
2) Parse for names, roles, and visible emails.
3) Infer email pattern from any found emails.
4) Generate candidate emails for target roles.
5) Check domain MX records (deliverability sanity).
6) Enrich with basic tech signals; de-dup, score, export.
    """)

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

target_roles = st.multiselect(
    "Target roles for candidate email generation",
    ["CEO","Founder","Co-Founder","Head of Growth","Growth","Marketing","Demand Gen","Sales","CTO","Product"],
    default=["Head of Growth","Marketing","Demand Gen","Sales","Founder","CEO"]
)

run = st.button("Run Enrich & Verify", type="primary", use_container_width=True)

if run and domains:
    rows = []
    for url in domains:
        bundle = fetch_site_bundle(url)
        found_people, found_emails = extract_people_and_emails(bundle)
        company = enrich_company(bundle)

        pattern_info = infer_patterns(found_emails, company.get("domain"))
        candidates = []
        for p in found_people:
            if any(r.lower() in (p.get("role","").lower()) for r in [r.lower() for r in target_roles]):
                candidates.extend(generate_candidates(p, company.get("domain"), pattern_info))

        mx_ok = check_mx(company.get("domain"))

        all_people = found_people + candidates
        all_people = dedupe_people(all_people)

        scored = score_leads(all_people, mx_ok=mx_ok, signals=company, pattern=pattern_info)

        for s in scored:
            s["company_name"] = company.get("name")
            s["company_domain"] = company.get("domain")
            s["tech_summary"] = ", ".join(company.get("tech_stack", [])[:6])
            s["mx_ok"] = mx_ok
            s["pattern"] = pattern_info.get("best_pattern")
            rows.append(s)

    if rows:
        out = pd.DataFrame(rows)
        st.success(f"Done. {len(out)} leads generated/enriched.")
        st.dataframe(out, use_container_width=True, height=500)

        csv = out.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", data=csv, file_name="leads_enriched.csv", mime="text/csv", use_container_width=True)

        st.caption("Tip: Import into your CRM; filter by `lead_score` and `mx_ok` first.")
    else:
        st.warning("No leads found. Try different sites or broaden target roles.")
elif run:
    st.warning("Please add at least one URL.")
