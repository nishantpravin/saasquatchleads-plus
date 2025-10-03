import asyncio
import aiosmtplib
import dns.resolver
from ratelimit import limits, sleep_and_retry
from tenacity import retry, stop_after_attempt, wait_fixed

# Per-minute rate limit (adjust in app UI if needed—here fixed at 30/min)
PER_MINUTE = 30

@sleep_and_retry
@limits(calls=PER_MINUTE, period=60)
@retry(stop=stop_after_attempt(2), wait=wait_fixed(0.5))
async def verify_single(recipient: str, mail_from: str = "noreply@example.com", timeout: float = 6.0) -> bool:
    """
    Lightweight SMTP RCPT verification:
    1) Resolve MX for recipient domain
    2) Connect and issue: EHLO, MAIL FROM, RCPT TO
    3) Do NOT send DATA; close
    Returns True if 250-class response for RCPT, else False.
    """
    try:
        local, domain = recipient.split("@", 1)
        mx_answers = dns.resolver.resolve(domain, "MX", lifetime=3.0)
        mx_hosts = sorted([(r.preference, str(r.exchange).rstrip(".")) for r in mx_answers], key=lambda x: x[0])
        if not mx_hosts:
            return False

        pref, host = mx_hosts[0]
        client = aiosmtplib.SMTP(hostname=host, port=25, timeout=timeout)
        await client.connect()
        code, _ = await client.ehlo()
        if code // 100 != 2:
            await client.quit()
            return False

        code, _ = await client.mail(mail_from)
        if code // 100 != 2:
            await client.quit()
            return False

        code, _ = await client.rcpt(recipient)
        await client.quit()
        return 200 <= code < 300
    except Exception:
        return False

async def verify_batch(emails, mail_from: str, per_minute: int = PER_MINUTE):
    # simple sequential with global limit from decorator; could be improved with concurrency<=N
    results = {}
    for em in emails:
        ok = await verify_single(em, mail_from=mail_from)
        results[em] = ok
    return results
