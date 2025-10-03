from bs4 import BeautifulSoup
import re
from .utils import EMAIL_RE, clean_text

NAME_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b")

ROLE_HINTS = [
    "CEO","Chief Executive","Founder","Co-Founder","Head of Growth","Growth",
    "Marketing","Demand Generation","Sales","CTO","CRO","CMO","VP","Director","Lead","Product"
]

def likely_role(txt: str) -> bool:
    t = txt.lower()
    return any(h.lower() in t for h in ROLE_HINTS)

def extract_people_and_emails(bundle: dict):
    people = []
    emails = set()
    for path, html in (bundle.get("pages") or {}).items():
        soup = BeautifulSoup(html, "lxml")
        text = " ".join(s.get_text(" ", strip=True) for s in soup.find_all(["p","li","h1","h2","h3","h4","span","a","div"]))
        # emails
        for em in re.findall(EMAIL_RE, text):
            emails.add(em.lower())

        # naive people extraction
        blocks = []
        for tag in soup.find_all(["h1","h2","h3","h4","p","li","span"]):
            blocks.append(clean_text(tag.get_text(" ", strip=True)))
        joined = " || ".join(b for b in blocks if b)

        for chunk in joined.split("||"):
            ck = clean_text(chunk)
            if len(ck) < 5:
                continue
            if likely_role(ck):
                m = NAME_RE.search(ck)
                if m:
                    name = m.group(1)
                    people.append({"name": name, "role": ck[:120]})

    uniq = []
    seen = set()
    for p in people:
        key = (p.get("name","").lower(), p.get("role","").lower())
        if key not in seen:
            seen.add(key)
            uniq.append(p)

    return uniq, list(emails)
