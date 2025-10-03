import os
import requests
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed

def push_hubspot_contacts(rows):
    """
    Expects HUBSPOT_ACCESS_TOKEN in env.
    Creates/updates contacts by email. Basic example (v3).
    """
    token = os.getenv("HUBSPOT_ACCESS_TOKEN")
    if not token:
        return {"ok": False, "reason": "no_token"}
    url = "https://api.hubapi.com/crm/v3/objects/contacts/batch/create"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    inputs = []
    for r in rows:
        email = r.get("email")
        if not email: 
            continue
        props = {
            "email": email,
            "firstname": (r.get("name") or "").split(" ")[0],
            "lastname": (r.get("name") or "").split(" ")[-1],
            "jobtitle": r.get("role"),
            "company": r.get("company_name"),
            "website": r.get("company_domain"),
            "notes": f"Lead score: {r.get('lead_score')}, MX: {r.get('mx_ok')}, pattern: {r.get('pattern')}"
        }
        inputs.append({"properties": props})
    if not inputs:
        return {"ok": False, "reason": "no_contacts"}
    resp = requests.post(url, headers=headers, json={"inputs": inputs}, timeout=12)
    if 200 <= resp.status_code < 300:
        return {"ok": True, "count": len(inputs)}
    return {"ok": False, "status": resp.status_code, "text": resp.text[:300]}

def push_salesforce_leads(rows):
    """
    Expects SF_USERNAME, SF_PASSWORD, SF_SECURITY_TOKEN, SF_DOMAIN in env.
    Creates Leads (minimal fields).
    """
    try:
        sf = Salesforce(
            username=os.getenv("SF_USERNAME"),
            password=os.getenv("SF_PASSWORD"),
            security_token=os.getenv("SF_SECURITY_TOKEN"),
            domain=os.getenv("SF_DOMAIN","login"),
        )
    except SalesforceAuthenticationFailed as e:
        return {"ok": False, "reason": f"auth_failed:{e}"}
    created = 0
    for r in rows:
        email = r.get("email")
        if not email: 
            continue
        payload = {
            "FirstName": (r.get("name") or "").split(" ")[0],
            "LastName": (r.get("name") or "").split(" ")[-1] or "Unknown",
            "Company": r.get("company_name") or "Unknown",
            "Title": r.get("role"),
            "Email": email,
            "Website": r.get("company_domain"),
            "Description": f"Lead score {r.get('lead_score')}, MX {r.get('mx_ok')}, Pattern {r.get('pattern')}"
        }
        try:
            res = sf.Lead.create(payload)
            if res.get("success"):
                created += 1
        except Exception:
            pass
    return {"ok": True, "created": created}
