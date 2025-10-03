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

# Revolutionary CSS Design - Like Nothing You've Seen Before
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .main-container {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 25%, #16213e 50%, #0f3460 75%, #533483 100%);
        min-height: 100vh;
        padding: 0;
        margin: 0;
    }
    
    .main-header {
        background: linear-gradient(135deg, #ff006e 0%, #8338ec 25%, #3a86ff 50%, #06ffa5 75%, #ffbe0b 100%);
        background-size: 400% 400%;
        animation: gradientShift 8s ease infinite;
        padding: 3rem 2rem;
        border-radius: 20px;
        margin-bottom: 3rem;
        text-align: center;
        color: white;
        position: relative;
        overflow: hidden;
        box-shadow: 0 20px 40px rgba(255, 0, 110, 0.3);
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><circle cx="25" cy="25" r="1" fill="rgba(255,255,255,0.1)"/><circle cx="75" cy="75" r="1" fill="rgba(255,255,255,0.1)"/><circle cx="50" cy="10" r="0.5" fill="rgba(255,255,255,0.05)"/></pattern></defs><rect width="100" height="100" fill="url(%23grain)"/></svg>');
        opacity: 0.3;
    }
    
    .main-header h1 {
        font-size: 3.5rem;
        font-weight: 900;
        margin: 0;
        text-shadow: 0 0 30px rgba(255, 255, 255, 0.5);
        position: relative;
        z-index: 1;
    }
    
    .main-header h3 {
        font-size: 1.5rem;
        font-weight: 600;
        margin: 1rem 0;
        opacity: 0.95;
        position: relative;
        z-index: 1;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    .feature-card {
        background: linear-gradient(145deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05));
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 2rem;
        border-radius: 20px;
        margin: 1.5rem 0;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .feature-card:hover {
        transform: translateY(-10px);
        box-shadow: 0 20px 40px rgba(255, 0, 110, 0.2);
        border-color: rgba(255, 0, 110, 0.5);
    }
    
    .feature-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
        transition: left 0.5s ease;
    }
    
    .feature-card:hover::before {
        left: 100%;
    }
    
    .feature-card h4 {
        color: #fff;
        font-size: 1.5rem;
        font-weight: 700;
        margin: 0 0 0.5rem 0;
        background: linear-gradient(45deg, #ff006e, #8338ec);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .feature-card p {
        color: rgba(255, 255, 255, 0.8);
        font-size: 1rem;
        margin: 0;
    }
    
    .metric-card {
        background: linear-gradient(145deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05));
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 2rem;
        border-radius: 20px;
        text-align: center;
        margin: 1rem 0;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .metric-card:hover {
        transform: scale(1.05);
        box-shadow: 0 15px 30px rgba(131, 56, 236, 0.3);
    }
    
    .metric-card h3 {
        color: rgba(255, 255, 255, 0.7);
        font-size: 1rem;
        font-weight: 600;
        margin: 0 0 1rem 0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .metric-card h2 {
        color: #fff;
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0;
        text-shadow: 0 0 20px rgba(255, 255, 255, 0.3);
    }
    
    .section-header {
        background: linear-gradient(135deg, #ff006e 0%, #8338ec 100%);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 15px;
        margin: 2rem 0 1rem 0;
        font-weight: 700;
        font-size: 1.3rem;
        text-align: center;
        box-shadow: 0 10px 25px rgba(255, 0, 110, 0.3);
        position: relative;
        overflow: hidden;
    }
    
    .section-header::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(45deg, transparent 30%, rgba(255, 255, 255, 0.1) 50%, transparent 70%);
        transform: translateX(-100%);
        animation: shimmer 2s infinite;
    }
    
    @keyframes shimmer {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }
    
    .consent-box {
        background: linear-gradient(145deg, rgba(6, 255, 165, 0.1), rgba(6, 255, 165, 0.05));
        backdrop-filter: blur(15px);
        border: 2px solid rgba(6, 255, 165, 0.3);
        border-radius: 15px;
        padding: 2rem;
        margin: 1.5rem 0;
        position: relative;
        overflow: hidden;
    }
    
    .consent-box::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: radial-gradient(circle at 30% 20%, rgba(6, 255, 165, 0.1) 0%, transparent 50%);
    }
    
    .config-section {
        background: linear-gradient(145deg, rgba(58, 134, 255, 0.1), rgba(58, 134, 255, 0.05));
        backdrop-filter: blur(15px);
        border: 1px solid rgba(58, 134, 255, 0.2);
        padding: 2rem;
        border-radius: 15px;
        margin: 1.5rem 0;
        position: relative;
        overflow: hidden;
    }
    
    .config-section::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: radial-gradient(circle at 70% 30%, rgba(58, 134, 255, 0.1) 0%, transparent 50%);
    }
    
    .status-success {
        background: linear-gradient(145deg, rgba(6, 255, 165, 0.2), rgba(6, 255, 165, 0.1));
        color: #06ffa5;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #06ffa5;
        backdrop-filter: blur(10px);
    }
    
    .status-warning {
        background: linear-gradient(145deg, rgba(255, 190, 11, 0.2), rgba(255, 190, 11, 0.1));
        color: #ffbe0b;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #ffbe0b;
        backdrop-filter: blur(10px);
    }
    
    .status-error {
        background: linear-gradient(145deg, rgba(255, 0, 110, 0.2), rgba(255, 0, 110, 0.1));
        color: #ff006e;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #ff006e;
        backdrop-filter: blur(10px);
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #ff006e, #8338ec);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #8338ec, #3a86ff);
    }
    
    /* Floating particles effect */
    .particles {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: -1;
    }
    
    .particle {
        position: absolute;
        width: 2px;
        height: 2px;
        background: rgba(255, 255, 255, 0.5);
        border-radius: 50%;
        animation: float 6s infinite linear;
    }
    
    @keyframes float {
        0% {
            transform: translateY(100vh) rotate(0deg);
            opacity: 0;
        }
        10% {
            opacity: 1;
        }
        90% {
            opacity: 1;
        }
        100% {
            transform: translateY(-100px) rotate(360deg);
            opacity: 0;
        }
    }
    
    /* Glassmorphism buttons */
    .stButton > button {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05));
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 15px;
        color: white;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 8px 32px rgba(255, 0, 110, 0.1);
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, rgba(255, 0, 110, 0.3), rgba(131, 56, 236, 0.3));
        transform: translateY(-2px);
        box-shadow: 0 15px 40px rgba(255, 0, 110, 0.3);
    }
    
    /* Input styling */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > select {
        background: rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 10px !important;
        color: white !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #ff006e !important;
        box-shadow: 0 0 20px rgba(255, 0, 110, 0.3) !important;
    }
    
    /* Checkbox styling */
    .stCheckbox > label > div[data-testid="stMarkdownContainer"] > p {
        color: rgba(255, 255, 255, 0.9) !important;
        font-weight: 500;
    }
    
    /* Multiselect styling */
    .stMultiSelect > div > div > div {
        background: rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 10px !important;
    }
    
    /* Slider styling */
    .stSlider > div > div > div > div {
        background: linear-gradient(90deg, #ff006e, #8338ec) !important;
    }
    
    /* Progress bar styling */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #ff006e, #8338ec, #3a86ff, #06ffa5) !important;
    }
    
    /* Dataframe styling */
    .dataframe {
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 15px !important;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom animations */
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    .pulse {
        animation: pulse 2s infinite;
    }
</style>

<!-- Floating Particles -->
<div class="particles">
    <div class="particle" style="left: 10%; animation-delay: 0s;"></div>
    <div class="particle" style="left: 20%; animation-delay: 1s;"></div>
    <div class="particle" style="left: 30%; animation-delay: 2s;"></div>
    <div class="particle" style="left: 40%; animation-delay: 3s;"></div>
    <div class="particle" style="left: 50%; animation-delay: 4s;"></div>
    <div class="particle" style="left: 60%; animation-delay: 5s;"></div>
    <div class="particle" style="left: 70%; animation-delay: 0.5s;"></div>
    <div class="particle" style="left: 80%; animation-delay: 1.5s;"></div>
    <div class="particle" style="left: 90%; animation-delay: 2.5s;"></div>
</div>
""", unsafe_allow_html=True)

st.set_page_config(
    page_title="SaaSquatchLeads+ Pro", 
    page_icon="🚀", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Revolutionary Header Section
st.markdown("""
<div class="main-header">
    <h1>🚀 SaaSquatchLeads+ Pro</h1>
    <h3>✨ AI-Powered Lead Enrichment & Verification Platform ✨</h3>
    <p style="font-size: 1.2rem; margin-top: 1rem; opacity: 0.9;">🔮 Extract • 🧠 Enrich • ⚡ Verify • 🎯 Push</p>
</div>
""", unsafe_allow_html=True)

# Revolutionary Features Overview
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("""
    <div class="feature-card">
        <h4>🧠 Neural AI</h4>
        <p>Advanced spaCy-powered intelligence</p>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown("""
    <div class="feature-card">
        <h4>🔮 Quantum Enrich</h4>
        <p>Wappalyzer & Firmographics APIs</p>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown("""
    <div class="feature-card">
        <h4>⚡ Lightning Verify</h4>
        <p>Ultra-fast SMTP validation</p>
    </div>
    """, unsafe_allow_html=True)
with col4:
    st.markdown("""
    <div class="feature-card">
        <h4>🎯 Precision Push</h4>
        <p>Direct CRM integration</p>
    </div>
    """, unsafe_allow_html=True)

# Main Input Section
st.markdown('<div class="section-header">🔮 Quantum Data Input Portal</div>', unsafe_allow_html=True)

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
        "Company URLs", 
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
st.markdown('<div class="section-header">⚡ Neural Configuration Matrix</div>', unsafe_allow_html=True)

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
st.markdown('<div class="section-header">🚀 Quantum Execution Protocol</div>', unsafe_allow_html=True)

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

# Revolutionary Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: rgba(255, 255, 255, 0.7); padding: 2rem; background: linear-gradient(145deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02)); border-radius: 20px; margin-top: 2rem;">
    <h4 style="color: #06ffa5; margin-bottom: 1rem;">🔮 Quantum Pro Tips</h4>
    <p style="margin: 0.5rem 0;">💫 <strong>Enhanced Mode:</strong> Set up API keys in <code style="background: rgba(255, 0, 110, 0.2); color: #ff006e; padding: 0.2rem 0.5rem; border-radius: 5px;">.env</code> file for maximum power</p>
    <p style="margin: 0.5rem 0;">🧠 <strong>Neural Boost:</strong> Run <code style="background: rgba(131, 56, 236, 0.2); color: #8338ec; padding: 0.2rem 0.5rem; border-radius: 5px;">python -m spacy download en_core_web_sm</code></p>
    <p style="margin-top: 1rem; font-size: 0.9rem; opacity: 0.8;">✨ Powered by Advanced AI • Built for the Future ✨</p>
</div>
""", unsafe_allow_html=True)
