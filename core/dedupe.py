from rapidfuzz import fuzz

def dedupe_people(rows, name_col="name", email_col="email", threshold=93):
    out = []
    seen_emails = set()
    names = []
    for r in rows:
        em = (r.get(email_col) or "").lower()
        nm = (r.get(name_col) or "").strip()
        if em and em in seen_emails:
            continue
        dup = False
        for existing in names:
            if fuzz.token_set_ratio(existing.lower(), nm.lower()) >= threshold:
                dup = True
                break
        if dup:
            continue
        if em:
            seen_emails.add(em)
        names.append(nm)
        out.append(r)
    return out
