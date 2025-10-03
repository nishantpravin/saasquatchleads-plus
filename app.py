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

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    .feature-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    .status-success {
        background: #d4edda;
        color: #155724;
        padding: 0.5rem;
        border-radius: 5px;
        border-left: 4px solid #28a745;
    }
    .status-warning {
        background: #fff3cd;
        color: #856404;
        padding: 0.5rem;
        border-radius: 5px;
        border-left: 4px solid #ffc107;
    }
    .status-error {
        background: #f8d7da;
        color: #721c24;
        padding: 0.5rem;
        border-radius: 5px;
        border-left: 4px solid #dc3545;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        margin: 0.5rem 0;
    }
    .section-header {
        background: #667eea;
        color: white;
        padding: 0.75rem 1rem;
        border-radius: 5px;
        margin: 1rem 0 0.5rem 0;
        font-weight: bold;
    }
    .consent-box {
        background: #e3f2fd;
        border: 2px solid #2196f3;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .config-section {
        background: #f5f5f5;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

st.set_page_config(
    page_title="SaaSquatchLeads+ Pro", 
    page_icon="🚀", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Header Section
st.markdown("""
<div class="main-header">
    <h1>🚀 SaaSquatchLeads+ Pro</h1>
    <h3>AI-Powered Lead Enrichment & Verification Platform</h3>
    <p>Extract • Enrich • Verify • Push to CRM</p>
</div>
""", unsafe_allow_html=True)

# Features Overview
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("""
    <div class="feature-card">
        <h4>🧠 AI NER</h4>
        <p>spaCy-powered name/role extraction</p>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown("""
    <div class="feature-card">
        <h4>🔌 API Enrich</h4>
        <p>Wappalyzer & Firmographics</p>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown("""
    <div class="feature-card">
        <h4>📧 SMTP Verify</h4>
        <p>Rate-limited with consent</p>
    </div>
    """, unsafe_allow_html=True)
with col4:
    st.markdown("""
    <div class="feature-card">
        <h4>🎯 CRM Push</h4>
        <p>HubSpot & Salesforce</p>
    </div>
    """, unsafe_allow_html=True)

# Main Input Section
st.markdown('<div class="section-header">📥 Data Input</div>', unsafe_allow_html=True)

input_mode = st.radio(
    "Choose input method:", 
    ["📋 Paste URLs", "📁 Upload CSV"], 
    horizontal=True,
    help="Select how you want to provide company data"
)

domains = []
if input_mode == "📋 Paste URLs":
    st.markdown("**Enter company URLs (one per line):**")
    urls_text = st.text_area(
        "", 
        height=120, 
        placeholder="https://example.com\nhttps://another-company.io\nhttps://startup.co",
        help="Paste company homepage URLs to analyze"
    )
    if urls_text.strip():
        domains = [u.strip() for u in urls_text.splitlines() if u.strip()]
else:
    st.markdown("**Upload CSV file with company data:**")
    up = st.file_uploader(
        "Choose CSV file", 
        type=["csv"],
        help="CSV should contain columns: company, url"
    )
    if up is not None:
        try:
            df_in = pd.read_csv(up)
            if not {"company","url"}.issubset(df_in.columns):
                st.error("❌ CSV must contain columns: 'company' and 'url'")
            else:
                domains = df_in["url"].dropna().astype(str).tolist()
                st.success(f"✅ Loaded {len(domains)} URLs from CSV")
        except Exception as e:
            st.error(f"❌ Error reading CSV: {str(e)}")

# Configuration Section
st.markdown('<div class="section-header">⚙️ Configuration</div>', unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("**🎯 Target Roles**")
    target_roles = st.multiselect(
        "Select roles to target for email generation:",
        ["CEO","Founder","Co-Founder","Head of Growth","Growth","Marketing","Demand Gen","Sales","CTO","Product","VP","Director"],
        default=["Head of Growth","Marketing","Demand Gen","Sales","Founder","CEO"],
        help="These roles will be prioritized for email candidate generation"
    )
    
    st.markdown("**🔌 API Enrichment**")
    do_wapp = st.checkbox(
        "🧪 Wappalyzer API", 
        value=True,
        help="Use Wappalyzer API for enhanced tech stack detection (requires WAPPALYZER_API_KEY)"
    )
    do_firmo = st.checkbox(
        "🏢 Firmographics API", 
        value=False,
        help="Use custom firmographics API for company data (requires FIRMO_API_URL & FIRMO_API_KEY)"
    )

with col2:
    st.markdown('<div class="consent-box">', unsafe_allow_html=True)
    st.markdown("**📧 SMTP Verification**")
    st.markdown("*⚠️ Legal consent required*")
    
    consent = st.checkbox(
        "✅ I have legal consent to verify emails for these domains", 
        value=False,
        help="You must have proper legal basis to verify emails"
    )
    
    if consent:
        smtp_rate = st.slider(
            "Verifications per minute:", 
            5, 120, 30,
            help="Rate limiting to prevent abuse"
        )
        smtp_from = st.text_input(
            "MAIL FROM address:", 
            os.getenv("SMTP_FROM","noreply@example.com"),
            help="Email address used in SMTP handshake"
        )
    else:
        st.info("🔒 SMTP verification disabled - consent required")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="config-section">', unsafe_allow_html=True)
    st.markdown("**🎯 CRM Integration**")
    push_hubspot = st.checkbox(
        "🔵 HubSpot Push", 
        value=False,
        help="Push leads to HubSpot (requires HUBSPOT_ACCESS_TOKEN)"
    )
    push_salesf = st.checkbox(
        "🟠 Salesforce Push", 
        value=False,
        help="Push leads to Salesforce (requires SF_* credentials)"
    )
    st.markdown('</div>', unsafe_allow_html=True)

# Action Button
st.markdown('<div class="section-header">🚀 Execute</div>', unsafe_allow_html=True)

if domains:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        run = st.button(
            "🚀 Start Lead Enrichment", 
            type="primary", 
            use_container_width=True,
            help="Begin the lead enrichment process with selected configurations"
        )
else:
    st.info("👆 Please provide company URLs or upload a CSV file to begin")
    run = False

if run and domains:
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    rows = []
    total_domains = len(domains)
    
    for i, url in enumerate(domains):
        status_text.text(f"🔄 Processing {i+1}/{total_domains}: {url}")
        progress_bar.progress((i + 1) / total_domains)
        
        try:
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
                
        except Exception as e:
            st.error(f"❌ Error processing {url}: {str(e)}")
            continue

    progress_bar.empty()
    status_text.empty()

    # Results Section
    if rows:
        out = pd.DataFrame(rows)
        
        # Metrics Dashboard
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("""
            <div class="metric-card">
                <h3>📊 Total Leads</h3>
                <h2 style="color: #667eea;">{}</h2>
            </div>
            """.format(len(out)), unsafe_allow_html=True)
        with col2:
            companies = len(out['company_name'].unique()) if 'company_name' in out.columns else 0
            st.markdown("""
            <div class="metric-card">
                <h3>🏢 Companies</h3>
                <h2 style="color: #28a745;">{}</h2>
            </div>
            """.format(companies), unsafe_allow_html=True)
        with col3:
            emails = len(out[out['email'].notna()]) if 'email' in out.columns else 0
            st.markdown("""
            <div class="metric-card">
                <h3>📧 Emails Found</h3>
                <h2 style="color: #17a2b8;">{}</h2>
            </div>
            """.format(emails), unsafe_allow_html=True)
        with col4:
            mx_valid = len(out[out['mx_ok'] == True]) if 'mx_ok' in out.columns else 0
            st.markdown("""
            <div class="metric-card">
                <h3>✅ MX Valid</h3>
                <h2 style="color: #ffc107;">{}</h2>
            </div>
            """.format(mx_valid), unsafe_allow_html=True)
        
        st.markdown('<div class="section-header">📋 Results</div>', unsafe_allow_html=True)
        
        # Enhanced Results Table
        st.dataframe(
            out, 
            use_container_width=True, 
            height=400,
            column_config={
                "lead_score": st.column_config.ProgressColumn(
                    "Lead Score",
                    help="Lead quality score (1-100)",
                    min_value=0,
                    max_value=100,
                ),
                "mx_ok": st.column_config.CheckboxColumn(
                    "MX Valid",
                    help="Domain has valid MX records"
                ),
                "email": st.column_config.TextColumn(
                    "Email",
                    help="Contact email address"
                ),
                "company_name": st.column_config.TextColumn(
                    "Company",
                    help="Company name"
                ),
                "role": st.column_config.TextColumn(
                    "Role",
                    help="Person's role/title"
                )
            }
        )

        # Download Section
        col1, col2 = st.columns(2)
        with col1:
            csv = out.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download CSV", 
                data=csv, 
                file_name="leads_enriched.csv", 
                mime="text/csv", 
                use_container_width=True,
                type="primary"
            )

        # SMTP Verification
        if consent and smtp_from and len(out):
            st.markdown('<div class="section-header">📧 SMTP Verification</div>', unsafe_allow_html=True)
            
            with st.spinner("🔄 Running SMTP verification (rate-limited)..."):
                emails = [e for e in out["email"].dropna().unique().tolist() if "@" in e]
                from core import smtp_verify as sv
                sv.PER_MINUTE = smtp_rate
                results = asyncio.run(verify_batch(emails, mail_from=smtp_from, per_minute=smtp_rate))
                out["smtp_verified"] = out["email"].map(results).fillna(False)
            
            verified_count = sum(results.values()) if results else 0
            st.success(f"✅ SMTP verification complete: {verified_count}/{len(emails)} emails verified")
            
            with col2:
                csv2 = out.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "📥 Download CSV + SMTP", 
                    data=csv2, 
                    file_name="leads_enriched_smtp.csv", 
                    mime="text/csv", 
                    use_container_width=True
                )
                
            st.dataframe(out, use_container_width=True, height=400)
            
        elif not consent and len(out) > 0:
            st.info("🔒 SMTP verification disabled - consent not provided")

        # CRM Push Section
        if (push_hubspot or push_salesf) and len(out) > 0:
            st.markdown('<div class="section-header">🎯 CRM Push</div>', unsafe_allow_html=True)
            
            sel = st.multiselect(
                "Select leads to push:", 
                list(range(len(out))), 
                format_func=lambda i: f"{out.iloc[i]['name']} — {out.iloc[i]['email']}", 
                max_selections=100,
                help="Choose which leads to push to your CRM"
            )
            
            if st.button("🚀 Push Selected Leads", type="primary", use_container_width=True):
                if sel:
                    push_rows = out.iloc[sel].to_dict("records")
                    
                    if push_hubspot:
                        with st.spinner("🔄 Pushing to HubSpot..."):
                            res_h = push_hubspot_contacts(push_rows)
                            if res_h.get("ok"):
                                st.success(f"✅ HubSpot: Successfully pushed {res_h.get('count',0)} contacts")
                            else:
                                st.error(f"❌ HubSpot push failed: {res_h}")
                    
                    if push_salesf:
                        with st.spinner("🔄 Pushing to Salesforce..."):
                            res_s = push_salesforce_leads(push_rows)
                            if res_s.get("ok"):
                                st.success(f"✅ Salesforce: Successfully created {res_s.get('created',0)} leads")
                            else:
                                st.error(f"❌ Salesforce push failed: {res_s}")
                else:
                    st.warning("👆 Please select leads to push")

    else:
        st.markdown('<div class="status-warning">⚠️ No leads found. Try different sites or broaden target roles.</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>💡 <strong>Pro Tips:</strong> Set up API keys in <code>.env</code> file for enhanced features</p>
    <p>🔧 For NER: Run <code>python -m spacy download en_core_web_sm</code></p>
</div>
""", unsafe_allow_html=True)
