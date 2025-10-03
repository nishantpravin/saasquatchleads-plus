import httpx
from .utils import get_domain

COMMON_PATHS = ["", "about", "team", "leadership", "company", "contact", "careers"]

def fetch(url: str) -> str:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (LeadQualityBot/1.0; +https://example.com/bot)"
        }
        with httpx.Client(follow_redirects=True, timeout=15) as client:
            r = client.get(url, headers=headers)
            if r.status_code == 200:
                return r.text
    except Exception:
        pass
    return ""

def normalize(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url.lstrip("/")
    return url.rstrip("/")

def fetch_site_bundle(url: str) -> dict:
    url = normalize(url)
    domain = get_domain(url)
    pages = {}
    for path in COMMON_PATHS:
        target = url if path == "" else f"{url}/{path}"
        html = fetch(target)
        if html:
            pages[path or "/"] = html
    return {"base_url": url, "domain": domain, "pages": pages}
