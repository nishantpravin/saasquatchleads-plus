import dns.resolver
from .utils import clean_text

PATTERNS = [
    "{first}@{domain}",
    "{first}.{last}@{domain}",
    "{f}{last}@{domain}",
    "{first}{l}@{domain}",
    "{f}.{last}@{domain}",
]

def split_name(full_name: str):
    parts = [p for p in clean_text(full_name).split() if p]
    if not parts:
        return None, None, None, None
    first = parts[0].lower()
    last = parts[-1].lower() if len(parts) > 1 else ""
    f = first[0] if first else ""
    l = last[0] if last else ""
    return first, last, f, l

def infer_patterns(found_emails, domain):
    counts = {}
    for em in (found_emails or []):
        try:
            local, host = em.split("@", 1)
            if host != domain:
                continue
            if "." in local and len(local.split(".")) == 2:
                counts["{first}.{last}@{domain}"] = counts.get("{first}.{last}@{domain}", 0) + 1
            elif len(local) > 1:
                counts["{first}@{domain}"] = counts.get("{first}@{domain}", 0) + 1
        except Exception:
            pass
    best = None
    if counts:
        best = max(counts, key=counts.get)
    return {"best_pattern": best, "counts": counts}

def generate_candidates(person: dict, domain: str, pattern_info: dict):
    first, last, f, l = split_name(person.get("name",""))
    if not first:
        return []
    pats = [pattern_info.get("best_pattern")] if pattern_info.get("best_pattern") else PATTERNS
    leads = []
    for p in pats:
        addr = p.format(first=first, last=last, f=f, l=l, domain=domain)
        leads.append({
            "name": person.get("name"),
            "role": person.get("role"),
            "email": addr.lower(),
            "source": "pattern"
        })
    return leads

def check_mx(domain: str) -> bool:
    try:
        answers = dns.resolver.resolve(domain, 'MX', lifetime=3.0)
        return len(list(answers)) > 0
    except Exception:
        return False
