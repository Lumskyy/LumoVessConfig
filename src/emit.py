import base64
import json
import os
import urllib.parse
import yaml
from src.rank import rebuild_raw
from src.parse import NAMES
from src.util import median, now_iso
from src.check import build_outbound


def ensure_dirs():
    os.makedirs("output" + os.sep + "countries", exist_ok=True)
    os.makedirs("docs", exist_ok=True)


def short_rtt(x):
    try:
        v = int(float(x.get("tcp_ms", 9999)))
        if v > 9999:
            v = 9999
        if v < 1:
            v = 1
        return v
    except Exception:
        return 9999


def pretty_name(kind, cc, idx, rtt, proto):
    cc = (cc or "UN").upper()
    proto = (proto or "vless").upper()
    name = NAMES.get(cc, cc)
    num = str(idx).zfill(2)
    tail = name + " · " + num + " · " + str(rtt) + "ms · " + proto
    if kind == "elite":
        return "🏆 ELITE · " + tail
    if kind == "best":
        return "⭐ BEST · " + tail
    if kind == "game":
        return "🎮 GAME · " + tail
    return tail


def rename_list(pairs, kind_mode="std"):
    out = []
    counters = {}
    for s, x in pairs:
        n = dict(x.get("node", {}))
        cc = str(n.get("country", "UN") or "UN").upper()
        proto = str(n.get("proto", "vless") or "vless").lower()
        rtt = short_rtt(x)
        counters[cc] = counters.get(cc, 0) + 1
        idx = counters[cc]
        name = pretty_name(kind_mode if kind_mode in ("elite", "best", "game") else "std", cc, idx, rtt, proto)
        raw = rebuild_raw(str(n.get("raw", "")), name)
        out.append({"name": name, "raw": raw, "node": n, "meta": x, "score": s})
    return out


def write_text_list(path, items):
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(it["raw"] + "\n")


def clash_proxy(it):
    n = it["node"]
    proto = str(n.get("proto", "")).lower()
    raw = str(n.get("raw", ""))
    name = it["name"]
    q = {}
    try:
        if "?" in raw:
            qq = raw.split("?", 1)[1].split("\u0023", 1)[0]
            q = dict(urllib.parse.parse_qsl(qq, keep_blank_values=True))
    except Exception:
        q = {}
    host = str(n.get("host", ""))
    port = int(n.get("port", 443))
    if proto == "vless":
        p = {"name": name, "type": "vless", "server": host, "port": port, "uuid": str(n.get("id", "")), "encryption": "none"}
        if str(n.get("flow", "")):
            p["flow"] = str(n.get("flow", ""))
        sec = str(n.get("security", "none") or "none").lower()
        if sec in ("tls", "reality"):
            p["tls"] = True
            p["servername"] = str(n.get("sni", "") or q.get("sni", "") or host)
            fp = str(q.get("fp", "") or q.get("fingerprint", "") or "chrome")
            p["client-fingerprint"] = fp
            if sec == "reality":
                p["reality-opts"] = {"public-key": str(q.get("pbk", "") or ""), "short-id": str(q.get("sid", "") or "")}
        t = str(n.get("transport", "tcp") or "tcp").lower()
        if t in ("ws", "websocket"):
            p["network"] = "ws"
            p["ws-opts"] = {"path": str(q.get("path", "/") or "/"), "headers": {"Host": str(q.get("host", "") or host)}}
        if t == "grpc":
            p["network"] = "grpc"
            p["grpc-opts"] = {"grpc-service-name": str(q.get("serviceName", "") or "")}
        return p
    if proto == "trojan":
        return {"name": name, "type": "trojan", "server": host, "port": port, "password": str(n.get("id", "")), "sni": str(n.get("sni", "") or host)}
    if proto == "vmess":
        return {"name": name, "type": "vmess", "server": host, "port": port, "uuid": str(n.get("id", "")), "alterId": 0, "cipher": "auto"}
    if proto == "ss":
        ident = str(n.get("id", ""))
        method = "aes-256-gcm"
        password = ident
        if ":" in ident and len(ident) < 200:
            method, password = ident.split(":", 1)
        return {"name": name, "type": "ss", "server": host, "port": port, "cipher": method, "password": password}
    return None


def write_clash(path, items):
    proxies = []
    for it in items:
        p = clash_proxy(it)
        if p:
            proxies.append(p)
    names = [p["name"] for p in proxies]
    data = {
        "proxies": proxies,
        "proxy-groups": [
            {"name": "Lumo-Auto", "type": "url-test", "proxies": names, "url": "http://www.gstatic.com/generate_204", "interval": 300},
            {"name": "Lumo-Select", "type": "select", "proxies": ["Lumo-Auto"] + names},
        ],
        "rules": ["MATCH,Lumo-Select"],
    }
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def write_singbox(path, items):
    outs = []
    for it in items:
        try:
            o = build_outbound(it["node"])
            o["tag"] = it["name"]
            outs.append(o)
        except Exception:
            continue
    tags = [o["tag"] for o in outs]
    cfg = {
        "log": {"level": "warn"},
        "inbounds": [{"type": "mixed", "tag": "in", "listen": "127.0.0.1", "listen_port": 1080}],
        "outbounds": outs + [{"type": "selector", "tag": "Lumo-Select", "outbounds": tags}, {"type": "urltest", "tag": "Lumo-Auto", "outbounds": tags, "url": "http://www.gstatic.com/generate_204", "interval": "5m"}],
        "route": {"rules": [], "final": "Lumo-Select"},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def write_all(best, elite, gaming, groups, all_items, stats):
    ensure_dirs()
    write_text_list(os.path.join("output", "happ-best.txt"), best)
    write_text_list(os.path.join("output", "happ-elite.txt"), elite)
    write_text_list(os.path.join("output", "happ-gaming.txt"), gaming)
    write_text_list(os.path.join("output", "happ-all.txt"), all_items)
    vless_only = [it for it in all_items if str(it["node"].get("proto", "")).lower() == "vless"]
    write_text_list(os.path.join("output", "happ-vless.txt"), vless_only)
    for cc, items in groups.items():
        renamed = rename_list(items, kind_mode="std")
        write_text_list(os.path.join("output", "countries", cc + ".txt"), renamed)
    cdir = os.path.join("output", "countries")
    for fn in os.listdir(cdir):
        if fn.endswith(".txt") and fn[:-4] not in groups:
            try:
                os.remove(os.path.join(cdir, fn))
            except Exception:
                pass
    with open(os.path.join("output", "v2ray.txt"), "w", encoding="utf-8") as f:
        blob = "\n".join([it["raw"] for it in all_items])
        f.write(base64.b64encode(blob.encode("utf-8")).decode("ascii"))
    write_clash(os.path.join("output", "clash.yaml"), all_items[:400])
    write_singbox(os.path.join("output", "singbox.json"), all_items[:400])
    with open(os.path.join("output", "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    with open(os.path.join("docs", "data.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def build_stats(total_in, parsed, checked_n, alive_pairs, best, elite, gaming, groups, sources_ok, sources_total, has_full, diag=None):
    tcps = [float(x.get("tcp_ms", 9999)) for _, x in alive_pairs if float(x.get("tcp_ms", 9999)) < 9999]
    https = [float(x.get("http_ms", 0)) for _, x in alive_pairs if float(x.get("http_ms", 0) or 0) > 0]
    udps = [float(x.get("udp_ms", 0)) for _, x in alive_pairs if float(x.get("udp_ms", 0) or 0) > 0]
    counts = {}
    for cc, items in groups.items():
        counts[cc] = len(items)
    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:24]
    return {
        "updated": now_iso(),
        "total_in": total_in,
        "parsed": parsed,
        "checked": checked_n,
        "alive": len(alive_pairs),
        "best": len(best),
        "elite": len(elite),
        "gaming": len(gaming),
        "countries": len(groups),
        "country_counts": dict(top),
        "median_tcp_ms": int(median(tcps)) if tcps else 0,
        "median_http_ms": int(median(https)) if https else 0,
        "median_udp_ms": int(median(udps)) if udps else 0,
        "sources_ok": sources_ok,
        "sources_total": sources_total,
        "full_probe": bool(has_full),
        "singbox": bool((diag or {}).get("singbox", False)),
        "fallback_tcp": bool((diag or {}).get("fallback_tcp", False)),
        "tcp_ok": int((diag or {}).get("tcp_ok", 0)),
        "full_ok": int((diag or {}).get("full_ok", 0)),
        "udp_ok": int((diag or {}).get("udp_ok", 0)),
        "leaked": int((diag or {}).get("leaked", 0)),
        "error": str((diag or {}).get("error", "")),
    }
