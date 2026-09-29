import base64
import json
import urllib.parse


def score_item(x, has_full):
    s = 0
    s = s + int(x.get("rounds_ok", 0)) * 30
    if x.get("leak"):
        s = s - 80
    g = int(x.get("google", 0))
    if g > 3:
        g = 3
    s = s + g * 8
    if int(x.get("cf", 0)) > 0:
        s = s + 15
    if x.get("full"):
        s = s + 25
    else:
        s = s + 5
    tcp = float(x.get("tcp_ms", 9999) or 9999)
    if tcp <= 150:
        s = s + 30
    elif tcp <= 250:
        s = s + 22
    elif tcp <= 400:
        s = s + 14
    elif tcp <= 700:
        s = s + 7
    http = float(x.get("http_ms", 0) or 0)
    if http and http <= 400:
        s = s + 18
    elif http and http <= 800:
        s = s + 10
    uo = int(x.get("udp_ok", 0))
    if uo >= 2:
        s = s + 12
    elif uo >= 1:
        s = s + 5
    n = x.get("node", {})
    proto = str(n.get("proto", "")).lower()
    sec = str(n.get("security", "") or "").lower()
    flow = str(n.get("flow", "") or "").lower()
    if proto == "vless" and sec == "reality":
        s = s + 10
    if "vision" in flow:
        s = s + 6
    if proto == "vless":
        s = s + 4
    if str(x.get("exit_ip", "") or "") and not x.get("leak"):
        s = s + 10
    if has_full:
        if not x.get("full"):
            s = s - 20
        if int(x.get("google", 0)) < 1 and int(x.get("cf", 0)) < 1:
            s = s - 25
    return s


def rebuild_raw(raw, new_tag):
    try:
        enc = urllib.parse.quote(new_tag, safe="")
        if raw.startswith("vmess://"):
            core = raw[len("vmess://"):].strip()
            frag = ""
            if "\u0023" in core:
                core = core.split("\u0023", 1)[0]
            pad = core + ("=" * (-len(core) % 4))
            obj = json.loads(base64.b64decode(pad).decode("utf-8", errors="strict"))
            obj["ps"] = new_tag
            txt = json.dumps(obj, separators=(",", ":"))
            return "vmess://" + base64.b64encode(txt.encode("utf-8")).decode("ascii") + "\u0023" + enc
        if "\u0023" in raw:
            head = raw.split("\u0023", 1)[0]
            return head + "\u0023" + enc
        return raw + "\u0023" + enc
    except Exception:
        return raw


def apply_name(node, new_tag):
    n = dict(node)
    n["tag"] = new_tag
    n["raw"] = rebuild_raw(str(n.get("raw", "")), new_tag)
    return n


def rank_all(checked):
    has_full = any(bool(x.get("full")) for x in checked)
    items = []
    for x in checked:
        s = score_item(x, has_full)
        items.append((s, x))
    items.sort(key=lambda t: t[0], reverse=True)
    alive = []
    for s, x in items:
        if x.get("leak"):
            continue
        if int(x.get("rounds_ok", 0)) < 2:
            continue
        if float(x.get("tcp_ms", 9999)) > 1200:
            continue
        if has_full and not x.get("full"):
            continue
        alive.append((s, x))
    if not alive:
        for s, x in items:
            if x.get("leak"):
                continue
            if int(x.get("rounds_ok", 0)) < 1:
                continue
            alive.append((s, x))
    return alive, has_full


def pick_best(alive, has_full, limit=120):
    out = []
    for s, x in alive:
        if has_full:
            if int(x.get("udp_ok", 0)) < 1 and float(x.get("http_ms", 0) or 9999) > 400:
                continue
        out.append((s, x))
    return out[:limit]


def pick_gaming(alive, has_full, limit=150):
    out = []
    for s, x in alive:
        n = x.get("node", {})
        tcp = float(x.get("tcp_ms", 9999))
        if tcp > 450:
            continue
        if has_full and int(x.get("udp_ok", 0)) < 1:
            continue
        if int(x.get("rounds_ok", 0)) < 3:
            if int(x.get("rounds_ok", 0)) < 2:
                continue
        proto = str(n.get("proto", "")).lower()
        if proto not in ("vless", "trojan", "vmess", "ss", "hysteria2", "tuic"):
            continue
        out.append((s, x))
    out.sort(key=lambda t: (0 if int(t[1].get("udp_ok", 0)) > 0 else 1, float(t[1].get("tcp_ms", 9999)), -t[0]))
    return out[:limit]


def pick_elite(alive, rounds_total, has_full, limit=80, per_country=8):
    cand = []
    for s, x in alive:
        if int(x.get("rounds_ok", 0)) < rounds_total:
            continue
        if x.get("leak"):
            continue
        n = x.get("node", {})
        tcp = float(x.get("tcp_ms", 9999))
        http = float(x.get("http_ms", 0) or 0)
        if has_full:
            if not x.get("full"):
                continue
            if not str(x.get("exit_ip", "") or ""):
                continue
            if int(x.get("google", 0)) < 2:
                continue
            if int(x.get("cf", 0)) < 1:
                continue
            if http <= 0 or http > 800:
                continue
            if tcp > 500:
                continue
            if str(n.get("proto", "")).lower() != "vless":
                continue
            if str(n.get("security", "") or "").lower() not in ("tls", "reality"):
                continue
            if int(x.get("udp_ok", 0)) < 2:
                continue
            udp = float(x.get("udp_ms", 0) or 0)
            if udp <= 0 or udp > 800:
                continue
            if float(x.get("udp_spread", 9999)) > 600:
                continue
        else:
            if tcp > 350:
                continue
        if float(x.get("tcp_spread", 9999)) > 250:
            continue
        if has_full and float(x.get("http_spread", 9999)) > 600:
            continue
        cand.append((s, x))
    cand.sort(key=lambda t: t[0], reverse=True)
    counts = {}
    out = []
    for s, x in cand:
        cc = str(x.get("node", {}).get("country", "UN") or "UN").upper()
        counts[cc] = counts.get(cc, 0) + 1
        if counts[cc] > per_country:
            continue
        out.append((s, x))
        if len(out) >= limit:
            break
    return out


def group_countries(alive, per=40):
    groups = {}
    for s, x in alive:
        cc = str(x.get("node", {}).get("country", "UN") or "UN").upper()
        groups.setdefault(cc, []).append((s, x))
    for cc in groups:
        groups[cc].sort(key=lambda t: t[0], reverse=True)
        groups[cc] = groups[cc][:per]
    return groups


def finalize(alive_best, alive_all):
    best_keys = set()
    for _, x in alive_best:
        n = x.get("node", {})
        best_keys.add(str(n.get("host", "")).lower() + ":" + str(n.get("port", "")) + ":" + str(n.get("id", ""))[:12])
    return best_keys
