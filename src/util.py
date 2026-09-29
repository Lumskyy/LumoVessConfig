import base64
import binascii
import datetime
import re


def decode_bytes(data):
    try:
        return data.decode("utf-8", errors="strict")
    except Exception:
        return data.decode("latin-1", errors="replace")


def maybe_b64_to_text(s):
    t = s.strip()
    if not t:
        return t
    if "://" in t:
        return t
    compact = re.sub(r"\s+", "", t)
    if len(compact) < 24:
        return t
    if len(compact) % 4 != 0:
        pad = 4 - (len(compact) % 4)
        compact = compact + ("=" * pad)
    try:
        raw = base64.b64decode(compact, validate=False)
        txt = raw.decode("utf-8", errors="strict")
        if "://" in txt:
            return txt
        return t
    except Exception:
        return t


def split_links(text):
    out = []
    for line in text.splitlines():
        s = line.strip().strip(",").strip('"').strip("'")
        if not s:
            continue
        if "://" not in s:
            continue
        out.append(s)
    return out


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def median(xs):
    if not xs:
        return 0
    ys = sorted(xs)
    n = len(ys)
    mid = n // 2
    if n % 2 == 1:
        return ys[mid]
    return (ys[mid - 1] + ys[mid]) / 2


def to_int(x, default=0):
    try:
        return int(str(x).strip())
    except Exception:
        return default


def clean_tag(s, limit=64):
    t = re.sub(r"\s+", " ", s or "").strip()
    t = t.replace("\n", " ").replace("\r", " ")
    if len(t) > limit:
        t = t[:limit].rstrip()
    return t
