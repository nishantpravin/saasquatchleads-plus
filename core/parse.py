from bs4 import BeautifulSoup
import re
from .utils import EMAIL_RE, clean_text
from .ner import extract_person_role_chunks, has_role_hint

NAME_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b")

def extract_people_and_emails(bundle: dict):
    people = []
    emails = set()
    for _, html in (bundle.get("pages") or {}).items():
        soup = BeautifulSoup(html, "lxml")
        # ALL TEXT
        text = " ".join(s.get_text(" ", strip=True) for s in soup.find_all(["p","li","h1","h2","h3","h4","span","a","div"]))
        # emails
        for em in re.findall(EMAIL_RE, text or ""):
            emails.add(em.lower())

        # 1) spaCy NER-based extraction
        ner_people = extract_person_role_chunks(text or "")
        people.extend(ner_people)

        # 2) Heuristic fallback (regex on role-bearing chunks)
        blocks = []
        for tag in soup.find_all(["h1","h2","h3","h4","p","li","span"]):
            blocks.append(clean_text(tag.get_text(" ", strip=True)))
        for ck in blocks:
            if len(ck) < 5:
                continue
            if has_role_hint(ck):
                m = NAME_RE.search(ck)
                if m:
                    name = m.group(1)
                    people.append({"name": name, "role": ck[:120]})

    # Deduplicate
    uniq, seen = [], set()
    for p in people:
        key = (p.get("name","").lower(), (p.get("role") or "").lower())
        if p.get("name") and key not in seen:
            seen.add(key)
            uniq.append(p)

    return uniq, list(emails)
