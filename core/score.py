def score_leads(rows, mx_ok: bool, signals: dict, pattern: dict):
    tech = set((signals or {}).get("tech_stack") or [])
    pattern_bonus = 8 if pattern.get("best_pattern") else 0
    mx_bonus = 10 if mx_ok else -5
    gtm = 5 if "Google Tag Manager" in tech else 0
    hubspot = 5 if "HubSpot" in tech else 0
    ga = 3 if "Google Analytics" in tech else 0

    out = []
    for r in rows:
        role = (r.get("role") or "").lower()
        role_weight = 0
        if any(k in role for k in ["growth","demand","marketing"]):
            role_weight = 12
        elif any(k in role for k in ["sales"]):
            role_weight = 8
        elif any(k in role for k in ["founder","ceo","co-founder","chief executive"]):
            role_weight = 6

        base = 50
        score = base + role_weight + pattern_bonus + mx_bonus + gtm + hubspot + ga
        r2 = {**r}
        r2["lead_score"] = max(1, min(100, score))
        out.append(r2)
    return out
