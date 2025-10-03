import re
import spacy

# Load once per process
try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = None  # app should handle missing model gracefully

ROLE_KEYWORDS = [
    "ceo","chief executive","founder","co-founder","growth","head of growth",
    "marketing","demand generation","demand gen","sales","cto","cmo","cro","vp","director","lead","product"
]

def extract_person_role_chunks(text: str):
    """
    Use spaCy NER to get PERSON entities, and tie them to nearby role keywords (window).
    """
    if not nlp:
        return []
    doc = nlp(text)
    people = []
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            # small window to find role hints around the entity's sent
            sent = ent.sent.text.lower()
            role_hit = None
            for kw in ROLE_KEYWORDS:
                if kw in sent:
                    role_hit = kw
                    break
            people.append({"name": ent.text.strip(), "role": role_hit or ""})
    # remove empties and dupes
    out, seen = [], set()
    for p in people:
        key = (p["name"].lower(), p["role"].lower())
        if p["name"] and key not in seen:
            seen.add(key)
            out.append(p)
    return out

def has_role_hint(s: str) -> bool:
    t = s.lower()
    return any(k in t for k in ROLE_KEYWORDS)
