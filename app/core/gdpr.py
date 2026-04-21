import re
from datetime import date, datetime, timezone


_PII_PATTERNS = [
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}\b"), "[EMAIL]"),
    (re.compile(r"\b(?:\+?34)?[\s-]?[6789]\d{2}[\s-]?\d{3}[\s-]?\d{3}\b"), "[PHONE]"),
    (re.compile(r"\b[XYZ]\d{7}[A-Z]\b|\b\d{8}[A-Z]\b"), "[ID_DOC]"),
    (re.compile(r"\b(?:\d[ -]?){13,16}\b"), "[CARD]"),
]


def scrub_pii(text: str) -> str:
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def get_session_ttl(checkout_date: date | None, ttl_hours: int = 24) -> int:
    if checkout_date is None:
        return ttl_hours * 3600
    expiry = datetime(
        checkout_date.year, checkout_date.month, checkout_date.day,
        tzinfo=timezone.utc,
    ).timestamp() + ttl_hours * 3600
    remaining = int(expiry - datetime.now(timezone.utc).timestamp())
    return max(remaining, ttl_hours * 3600)
