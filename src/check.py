import asyncio
import json
import os
import shutil
import socket
import ssl
import subprocess
import tempfile
import time
import urllib.parse
import httpx


GOOGLE_HTTP = "http://www.gstatic.com/generate_204"
GOOGLE_HTTPS = "https://www.google.com/generate_204"
CF_TRACE = "https://www.cloudflare.com/cdn-cgi/trace"
IP_ECHO = "https://api.ipify.org?format=text"
HEADERS_ECHO = "https://httpbin.org/headers"


def singbox_bin():
    v = os.environ.get("SINGBOX_BIN", "").strip()
    if v and os.path.exists(v):
        return v
    w = shutil.which("sing-box")
    if w:
        return w
    for p in ["/usr/local/bin/sing-box", "/opt/sing-box/sing-box"]:
        if os.path.exists(p):
            return p
    return ""


async def direct_text(url, timeout=15):
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as c:
            r = await c.get(url, headers={"User-Agent": "LumoVessConfig/1.0"})
            t = r.text.strip()
            return r.status_code, t
    except Exception:
        return 0, ""


async def get_public_ip():
    code, txt = await direct_text(IP_ECHO, timeout=15)
    t = txt.strip().split()[0] if txt.strip() else ""
    if code == 200 and len(t) >= 7 and "." in t:
        return t
    return ""


async def tcp_rtt(host, port, timeout=6):
    host = (host or "").strip()
    if not host:
        return None
    try:
        port = int(port)
    except Exception:
        return None
    loop = asyncio.get_running_loop()
    t0 = loop.time()
    try:
        fut = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(fut, timeout=timeout)
        dt = (loop.time() - t0) * 1000.0
        try:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
        except Exception:
            pass
        return dt
    except Exception:
        return None


async def tls_rtt(host, port, sni="", timeout=8):
    host = (host or "").strip()
    if not host:
        return None
    try:
        port = int(port)
    except Exception:
        return None
    name = (sni or "").strip() or host
    def blocking():
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        t0 = time.monotonic()
        s = socket.create_connection((host, port), timeout=timeout)
        try:
            s.settimeout(timeout)
            w = ctx.wrap_socket(s, server_hostname=name)
            try:
                w.do_handshake()
            except Exception:
                pass
            dt = (time.monotonic() - t0) * 1000.0
            try:
                w.close()
            except Exception:
                pass
            return dt
        finally:
            try:
                s.close()
            except Exception:
                pass
    try:
        return await asyncio.to_thread(blocking)
    except Exception:
        return None


def query_of(raw):
    try:
        q = raw.split("?", 1)[1]
        q = q.split("\u0023", 1)[0]
        return dict(urllib.parse.parse_qsl(q, keep_blank_values=True))
    except Exception:
        return {}


def build_outbound(node):
    proto = str(node.get("proto", "")).lower()
    host = str(node.get("host", ""))
    port = int(node.get("port", 443))
    raw = str(node.get("raw", ""))
    q = query_of(raw)
    transport = str(node.get("transport", "tcp") or "tcp").lower()
    security = str(node.get("security", "none") or "none").lower()
    out = {"type": proto if proto in ("vless", "vmess", "trojan", "shadowsocks") else "vless"}
    if proto == "shadowsocks" or (proto == "ss"):
        out["type"] = "shadowsocks"
        ident = str(node.get("id", ""))
        method = "aes-256-gcm"
        password = ident
        if ":" in ident and len(ident) < 200:
            method, password = ident.split(":", 1)
        out["server"] = host
        out["server_port"] = port
        out["method"] = method
        out["password"] = password
        return out
    if proto == "trojan":
        out["type"] = "trojan"
        out["server"] = host
        out["server_port"] = port
        out["password"] = str(node.get("id", ""))
        tls = {"enabled": True, "server_name": str(node.get("sni", "") or host)}
        fp = str(q.get("fp", "") or q.get("fingerprint", "") or "chrome")
        tls["utls"] = {"enabled": True, "fingerprint": fp}
        out["tls"] = tls
        if transport in ("ws", "websocket"):
            out["transport"] = {
                "type": "ws",
                "path": str(q.get("path", "/") or "/"),
                "headers": {"Host": str(q.get("host", "") or q.get("sni", "") or host)},
            }
        return out
    if proto == "vmess":
        out["type"] = "vmess"
        out["server"] = host
        out["server_port"] = port
        out["uuid"] = str(node.get("id", ""))
        out["alter_id"] = 0
        out["security"] = "auto"
        if security in ("tls", "reality"):
            out["tls"] = {"enabled": True, "server_name": str(node.get("sni", "") or host)}
        if transport in ("ws", "websocket"):
            out["transport"] = {"type": "ws", "path": str(q.get("path", "/") or "/")}
        return out
    out["type"] = "vless"
    out["server"] = host
    out["server_port"] = port
    out["uuid"] = str(node.get("id", ""))
    out["flow"] = str(node.get("flow", "") or q.get("flow", ""))
    if security in ("tls", "reality"):
        tls = {"enabled": True, "server_name": str(node.get("sni", "") or q.get("sni", "") or host)}
        fp = str(q.get("fp", "") or q.get("fingerprint", "") or "chrome")
        tls["utls"] = {"enabled": True, "fingerprint": fp}
        if security == "reality":
            tls["reality"] = {
                "enabled": True,
                "public_key": str(q.get("pbk", "") or q.get("publicKey", "") or ""),
                "short_id": str(q.get("sid", "") or q.get("shortId", "") or ""),
            }
        out["tls"] = tls
    ttype = transport
    if ttype == "websocket":
        ttype = "ws"
    if ttype in ("ws",):
        out["transport"] = {
            "type": "ws",
            "path": str(q.get("path", "/") or "/"),
            "headers": {"Host": str(q.get("host", "") or host)},
        }
    if ttype in ("grpc",):
        out["transport"] = {"type": "grpc", "service_name": str(q.get("serviceName", "") or q.get("service_name", "") or "")}
    if ttype in ("xhttp",):
        out["transport"] = {"type": "xhttp", "path": str(q.get("path", "/") or "/")}
    return out


async def probe_with_singbox(node, binpath, timeout=18):
    mixed = 18080
    try:
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        mixed = s.getsockname()[1]
        s.close()
    except Exception:
        mixed = 18080
    outbound = build_outbound(node)
    cfg = {
        "log": {"level": "error"},
        "inbounds": [{"type": "mixed", "tag": "mix", "listen": "127.0.0.1", "listen_port": mixed}],
        "outbounds": [dict(outbound, tag="out"), {"type": "direct", "tag": "direct"}],
        "route": {"rules": [{"outbound": "out", "network": ["tcp", "udp"]}]},
    }
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    try:
        json.dump(cfg, tmp)
        tmp.close()
        proc = await asyncio.create_subprocess_exec(
            binpath, "run", "-c", tmp.name,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.sleep(1.2)
        proxy = "http://127.0.0.1:" + str(mixed)
        proxies = {"http://": proxy, "https://": proxy}
        res = {"http_ms": [], "google": 0, "cf": 0, "exit_ip": "", "leak": False, "trace": ""}
        try:
            async with httpx.AsyncClient(proxies=proxies, timeout=timeout, follow_redirects=True) as c:
                t0 = time.monotonic()
                try:
                    r = await c.get(GOOGLE_HTTP)
                    if r.status_code == 204:
                        res["google"] = res["google"] + 1
                        res["http_ms"].append((time.monotonic() - t0) * 1000.0)
                except Exception:
                    pass
                t0 = time.monotonic()
                try:
                    r = await c.get(GOOGLE_HTTPS)
                    if r.status_code in (200, 204):
                        res["google"] = res["google"] + 1
                        res["http_ms"].append((time.monotonic() - t0) * 1000.0)
                except Exception:
                    pass
                try:
                    r = await c.get(CF_TRACE)
                    if r.status_code == 200 and "ip=" in r.text:
                        res["cf"] = 1
                        res["trace"] = r.text[:800]
                except Exception:
                    pass
                try:
                    r = await c.get(IP_ECHO)
                    if r.status_code == 200:
                        cand = r.text.strip().split()[0]
                        if len(cand) >= 7:
                            res["exit_ip"] = cand
                except Exception:
                    pass
                try:
                    r = await c.get(HEADERS_ECHO)
                    if r.status_code == 200:
                        res["headers_body"] = r.text[:1200]
                    else:
                        res["headers_body"] = ""
                except Exception:
                    res["headers_body"] = ""
        finally:
            try:
                proc.terminate()
            except Exception:
                pass
            try:
                await asyncio.wait_for(proc.wait(), timeout=4)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        return res
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


async def check_round(nodes, public_ip, binpath, limit=64):
    sem = asyncio.Semaphore(limit)
    out = {}

    async def one(n):
        async with sem:
            host = str(n.get("host", ""))
            port = int(n.get("port", 443))
            key = str(n.get("host", "")).lower() + ":" + str(port) + ":" + str(n.get("id", ""))[:8]
            r = {"tcp": None, "tls": None, "http_ms": [], "google": 0, "cf": 0, "exit_ip": "", "leak": False}
            r["tcp"] = await tcp_rtt(host, port, timeout=6)
            sec = str(n.get("security", "none") or "none").lower()
            if sec in ("tls", "reality"):
                r["tls"] = await tls_rtt(host, port, str(n.get("sni", "") or host), timeout=8)
            if binpath and r["tcp"] is not None:
                try:
                    full = await probe_with_singbox(n, binpath, timeout=16)
                    r["http_ms"] = full.get("http_ms", [])
                    r["google"] = full.get("google", 0)
                    r["cf"] = full.get("cf", 0)
                    r["exit_ip"] = full.get("exit_ip", "")
                    body = str(full.get("headers_body", "") or "").lower()
                    if public_ip and public_ip.lower() in body:
                        r["leak"] = True
                    if public_ip and r["exit_ip"] and r["exit_ip"].strip() == public_ip.strip():
                        r["leak"] = True
                except Exception:
                    pass
            out[key] = r
            return key, r

    await asyncio.gather(*[one(n) for n in nodes])
    return out


async def triple_check(nodes, rounds=3, delay=25, prefilter=1400, limit=64):
    nodes = list(nodes)
    if not nodes:
        return []
    public_ip = await get_public_ip()
    binpath = singbox_bin()
    sem = asyncio.Semaphore(limit)

    async def fast_tcp(n):
        async with sem:
            v = await tcp_rtt(str(n.get("host", "")), int(n.get("port", 443)), timeout=5)
            return v

    tcps = await asyncio.gather(*[fast_tcp(n) for n in nodes])
    scored = []
    for n, v in zip(nodes, tcps):
        if v is not None:
            scored.append((v, n))
    scored.sort(key=lambda x: x[0])
    cand = [n for _, n in scored[:prefilter]] if scored else []
    if not cand:
        return []
    agg = {}
    for n in cand:
        key = str(n.get("host", "")).lower() + ":" + str(n.get("port", "")) + ":" + str(n.get("id", ""))[:12]
        agg[key] = {"node": n, "tcp": [], "tls": [], "http": [], "google": 0, "cf": 0, "exit": "", "leak": False, "rounds_ok": 0}
    for i in range(rounds):
        res = await check_round(cand, public_ip, binpath, limit=limit)
        for n in cand:
            key = str(n.get("host", "")).lower() + ":" + str(n.get("port", "")) + ":" + str(n.get("id", ""))[:12]
            a = agg.get(key)
            if not a:
                continue
            k2 = str(n.get("host", "")).lower() + ":" + str(n.get("port", "")) + ":" + str(n.get("id", ""))[:8]
            r = res.get(k2)
            if not r:
                continue
            if r.get("tcp") is not None:
                a["tcp"].append(r["tcp"])
            if r.get("tls") is not None:
                a["tls"].append(r["tls"])
            if r.get("http_ms"):
                a["http"].extend(r["http_ms"])
            a["google"] = a["google"] + int(r.get("google", 0) or 0)
            a["cf"] = a["cf"] + int(r.get("cf", 0) or 0)
            if r.get("exit_ip"):
                a["exit"] = r["exit_ip"]
            if r.get("leak"):
                a["leak"] = True
            if r.get("tcp") is not None and (r.get("http_ms") or not binpath):
                a["rounds_ok"] = a["rounds_ok"] + 1
        if i < rounds - 1:
            try:
                await asyncio.sleep(delay)
            except Exception:
                pass
    final = []
    for key, a in agg.items():
        n = a["node"]
        tcps = sorted(a["tcp"])
        https = sorted(a["http"])
        tcp_spread = (tcps[-1] - tcps[0]) if len(tcps) > 1 else 0
        http_spread = (https[-1] - https[0]) if len(https) > 1 else 0
        final.append({
            "node": n,
            "tcp_ms": tcps[len(tcps) // 2] if tcps else 9999,
            "tls_ms": sorted(a["tls"])[len(a["tls"]) // 2] if a["tls"] else 0,
            "http_ms": https[len(https) // 2] if https else 0,
            "tcp_spread": tcp_spread,
            "http_spread": http_spread,
            "google": a["google"],
            "cf": a["cf"],
            "exit_ip": a["exit"],
            "leak": a["leak"],
            "rounds_ok": a["rounds_ok"],
            "full": bool(a["http"]),
        })
    return final
