from bs4 import BeautifulSoup
from .utils import clean_text

def sniff_tech(soup: BeautifulSoup) -> list:
    tech = set()
    for s in soup.find_all("script", src=True):
        src = s["src"].lower()
        if "gtm" in src or "googletagmanager" in src: tech.add("Google Tag Manager")
        if "analytics" in src: tech.add("Google Analytics")
        if "hotjar" in src: tech.add("Hotjar")
        if "segment" in src: tech.add("Segment")
        if "hubspot" in src: tech.add("HubSpot")
        if "intercom" in src: tech.add("Intercom")
        if "mixpanel" in src: tech.add("Mixpanel")
    for l in soup.find_all("link", href=True):
        href = l["href"].lower()
        if "wp-content" in href: tech.add("WordPress")
        if "shopify" in href: tech.add("Shopify")
        if "wix" in href: tech.add("Wix")
        if "webflow" in href: tech.add("Webflow")
    return sorted(tech)

def enrich_company(bundle: dict) -> dict:
    name = None
    tech_stack = set()
    for html in (bundle.get("pages") or {}).values():
        soup = BeautifulSoup(html, "lxml")
        if not name:
            if soup.title and soup.title.string:
                name = clean_text(soup.title.string.split("|")[0])
        tech_stack |= set(sniff_tech(soup))
    return {
        "name": name or bundle.get("domain"),
        "domain": bundle.get("domain"),
        "tech_stack": sorted(list(tech_stack))
    }
