import os
import json
import requests
from bs4 import BeautifulSoup
from .utils import clean_text

def wappalyzer_enrich(url: str):
    """
    Uses Wappalyzer API if WAPPALYZER_API_KEY set. Falls back to lightweight sniffing (client-side).
    """
    api_key = os.getenv("WAPPALYZER_API_KEY")
    if not api_key:
        return None, "no_api_key"
    try:
        resp = requests.get(
            "https://api.wappalyzer.com/v2/lookup/",
            params={"urls": url},
            headers={"x-api-key": api_key},
            timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data, "ok"
        return None, f"http_{resp.status_code}"
    except Exception as e:
        return None, f"error:{e}"

def firmographics_enrich(domain: str):
    """
    Optional firmographics enrichment via your API. 
    Provide FIRMO_API_URL + FIRMO_API_KEY in environment.
    Expected response fields: size, employees, founded_year, hq_country, linkedin
    """
    base = os.getenv("FIRMO_API_URL")
    key = os.getenv("FIRMO_API_KEY")
    if not base or not key:
        return None, "no_api"
    try:
        resp = requests.get(
            f"{base.rstrip('/')}/enrich",
            params={"domain": domain},
            headers={"Authorization": f"Bearer {key}"},
            timeout=8,
        )
        if resp.status_code == 200:
            return resp.json(), "ok"
        return None, f"http_{resp.status_code}"
    except Exception as e:
        return None, f"error:{e}"

def soup_title_name(html: str):
    soup = BeautifulSoup(html, "lxml")
    if soup.title and soup.title.string:
        return clean_text(soup.title.string.split("|")[0])
    return None
