import base64
import json
import re
import urllib.parse
from src.util import clean_tag


COUNTRY_HINTS = {
    "US": ["united states", "usa", "america", "los angeles", "new york", "dallas", "miami", "seattle", "ashburn", "chicago", "美国"],
    "JP": ["japan", "tokyo", "osaka", "japanese", "日本"],
    "SG": ["singapore", "新加坡"],
    "NL": ["netherlands", "holland", "amsterdam", "荷兰"],
    "DE": ["germany", "german", "frankfurt", "berlin", "munich", "德国"],
    "GB": ["united kingdom", "britain", "london", "england", "英国"],
    "FR": ["france", "french", "paris", "法国"],
    "CA": ["canada", "toronto", "vancouver", "加拿大"],
    "HK": ["hong kong", "香港"],
    "TW": ["taiwan", "taipei", "台湾"],
    "KR": ["korea", "seoul", "korean", "韩国"],
    "AU": ["australia", "sydney", "melbourne", "澳大利亚"],
    "IN": ["india", "mumbai", "delhi", "印度"],
    "BR": ["brazil", "paulo", "巴西"],
    "TR": ["turkey", "turkish", "istanbul", "土耳其"],
    "FI": ["finland", "helsinki", "芬兰"],
    "SE": ["sweden", "stockholm", "瑞典"],
    "NO": ["norway", "oslo", "挪威"],
    "PL": ["poland", "polska", "warsaw", "Польша", "波兰"],
    "IT": ["italy", "italian", "milan", "rome", "意大利"],
    "ES": ["spain", "madrid", "spanish", "西班牙"],
    "CH": ["switzerland", "zurich", "swiss", "瑞士"],
    "AT": ["austria", "vienna", "奥地利"],
    "IE": ["ireland", "dublin", "爱尔兰"],
    "RO": ["romania", "bucharest", "罗马尼亚"],
    "UA": ["ukraine", "kyiv", "kiev", "odessa", "lviv", "Украина", "乌克兰"],
    "KZ": ["kazakhstan", "almaty", "Казахстан"],
    "AE": ["emirates", "dubai", "arab", "阿联酋"],
    "IR": ["iran", "tehran", "伊朗"],
    "RU": ["russia", "moscow", "petersburg", "Россия", "俄罗斯"],
    "MY": ["malaysia", "kuala", "马来西亚"],
    "ID": ["indonesia", "jakarta", "印度尼西亚"],
    "TH": ["thailand", "bangkok", "泰国"],
    "VN": ["vietnam", "hanoi", "越南"],
    "PH": ["philippines", "manila", "菲律宾"],
    "MX": ["mexico", "墨西哥"],
    "AR": ["argentina", "阿根廷"],
    "CL": ["chile", "智利"],
    "CO": ["colombia", "哥伦比亚"],
    "ZA": ["south africa", "africa", "南非"],
    "EG": ["egypt", "埃及"],
    "IL": ["israel", "以色列"],
    "GR": ["greece", "希腊"],
    "PT": ["portugal", "葡萄牙"],
    "CZ": ["czechia", "czech", "prague", "捷克"],
    "HU": ["hungary", "budapest", "匈牙利"],
    "DK": ["denmark", "丹麦"],
    "BE": ["belgium", "比利时"],
    "LV": ["latvia", "拉脱维亚"],
    "LT": ["lithuania", "立陶宛"],
    "EE": ["estonia", "爱沙尼亚"],
    "HR": ["croatia", "克罗地亚"],
    "RS": ["serbia", "塞尔维亚"],
    "BG": ["bulgaria", "保加利亚"],
    "MD": ["moldova", "摩尔多瓦"],
    "GE": ["georgia", "tbilisi", "格鲁吉亚"],
    "AM": ["armenia", "亚美尼亚"],
    "AZ": ["azerbaijan", "阿塞拜疆"],
    "UZ": ["uzbekistan", "乌兹别克斯坦"],
}

FLAGS = {
    "US": "🇺🇸", "JP": "🇯🇵", "SG": "🇸🇬", "NL": "🇳🇱", "DE": "🇩🇪",
    "GB": "🇬🇧", "FR": "🇫🇷", "CA": "🇨🇦", "HK": "🇭🇰", "TW": "🇹🇼",
    "KR": "🇰🇷", "AU": "🇦🇺", "IN": "🇮🇳", "BR": "🇧🇷", "TR": "🇹🇷",
    "FI": "🇫🇮", "SE": "🇸🇪", "NO": "🇳🇴", "PL": "🇵🇱", "IT": "🇮🇹",
    "ES": "🇪🇸", "CH": "🇨🇭", "AT": "🇦🇹", "IE": "🇮🇪", "RO": "🇷🇴",
    "UA": "🇺🇦", "KZ": "🇰🇿", "AE": "🇦🇪", "IR": "🇮🇷", "RU": "🇷🇺",
    "MY": "🇲🇾", "ID": "🇮🇩", "TH": "🇹🇭", "VN": "🇻🇳", "PH": "🇵🇭",
    "MX": "🇲🇽", "AR": "🇦🇷", "CL": "🇨🇱", "CO": "🇨🇴", "ZA": "🇿🇦",
    "EG": "🇪🇬", "IL": "🇮🇱", "GR": "🇬🇷", "PT": "🇵🇹", "CZ": "🇨🇿",
    "HU": "🇭🇺", "DK": "🇩🇰", "BE": "🇧🇪", "LV": "🇱🇻", "LT": "🇱🇹",
    "EE": "🇪🇪", "HR": "🇭🇷", "RS": "🇷🇸", "BG": "🇧🇬", "MD": "🇲🇩",
    "GE": "🇬🇪", "AM": "🇦🇲", "AZ": "🇦🇿", "UZ": "🇺🇿",
}

NAMES = {
    "US": "United States", "JP": "Japan", "SG": "Singapore", "NL": "Netherlands",
    "DE": "Germany", "GB": "United Kingdom", "FR": "France", "CA": "Canada",
    "HK": "Hong Kong", "TW": "Taiwan", "KR": "South Korea", "AU": "Australia",
    "IN": "India", "BR": "Brazil", "TR": "Turkey", "FI": "Finland",
    "SE": "Sweden", "NO": "Norway", "PL": "Poland", "IT": "Italy",
    "ES": "Spain", "CH": "Switzerland", "AT": "Austria", "IE": "Ireland",
    "RO": "Romania", "UA": "Ukraine", "KZ": "Kazakhstan", "AE": "UAE",
    "IR": "Iran", "RU": "Russia", "MY": "Malaysia", "ID": "Indonesia",
    "TH": "Thailand", "VN": "Vietnam", "PH": "Philippines", "MX": "Mexico",
    "AR": "Argentina", "CL": "Chile", "CO": "Colombia", "ZA": "South Africa",
    "EG": "Egypt", "IL": "Israel", "GR": "Greece", "PT": "Portugal",
    "CZ": "Czechia", "HU": "Hungary", "DK": "Denmark", "BE": "Belgium",
    "LV": "Latvia", "LT": "Lithuania", "EE": "Estonia", "HR": "Croatia",
    "RS": "Serbia", "BG": "Bulgaria", "MD": "Moldova", "GE": "Georgia",
    "AM": "Armenia", "AZ": "Azerbaijan", "UZ": "Uzbekistan", "UN": "World",
}

CODE_RE = {}


def build_code_patterns():
    for code in COUNTRY_HINTS:
        CODE_RE[code] = re.compile(r"(?<![a-z])" + code.lower() + r"(?![a-z])")


build_code_patterns()


def guess_country(tag):
    t = tag or ""
    for code, flag in FLAGS.items():
        if flag and flag in t:
            return code
    low = t.lower()
    for code, names in COUNTRY_HINTS.items():
        for name in names:
            if name and name.lower() in low:
                return code
    for code, pat in CODE_RE.items():
        if pat.search(low):
            return code
    return "UN"


def parse_vless(link):
    try:
        body = link[len("vless://"):]
        tag = ""
        if "\u0023" in body:
            body, frag = body.split("\u0023", 1)
            tag = urllib.parse.unquote(frag)
        if "@" not in body:
            return None
        userinfo, hostinfo = body.rsplit("@", 1)
        uuid = urllib.parse.unquote(userinfo.strip())
        if "?" in hostinfo:
            hostport, query = hostinfo.split("?", 1)
        else:
            hostport, query = hostinfo, ""
        if ":" in hostport:
            host, port = hostport.rsplit(":", 1)
        else:
            host, port = hostport, "443"
        host = host.strip().strip("[]")
        try:
            port = int(str(port).strip())
        except Exception:
            return None
        q = urllib.parse.parse_qs(query, keep_blank_values=True)
        def one(k, d=""):
            v = q.get(k, [d])
            return v[0] if v else d
        node = {
            "raw": link,
            "proto": "vless",
            "id": uuid,
            "host": host,
            "port": port,
            "security": (one("security", "none") or "none").lower(),
            "transport": (one("type", "tcp") or "tcp").lower(),
            "sni": one("sni", one("serverName", one("host", ""))),
            "flow": one("flow", ""),
            "tag": clean_tag(tag) or (host + ":" + str(port)),
        }
        node["country"] = guess_country(node["tag"] + " " + host)
        return node
    except Exception:
        return None


def parse_vmess(link):
    try:
        b = link[len("vmess://"):].strip()
        if "\u0023" in b:
            b = b.split("\u0023", 1)[0]
        pad = b + ("=" * (-len(b) % 4))
        data = base64.b64decode(pad).decode("utf-8", errors="strict")
        obj = json.loads(data)
        host = str(obj.get("add", "")).strip()
        port = int(str(obj.get("port", "0")).strip() or 0)
        if not host or not port:
            return None
        tag = clean_tag(str(obj.get("ps", ""))) or (host + ":" + str(port))
        node = {
            "raw": link,
            "proto": "vmess",
            "id": str(obj.get("id", "")),
            "host": host,
            "port": port,
            "security": str(obj.get("tls", "") or obj.get("security", "none")).lower() or "none",
            "transport": str(obj.get("net", "tcp") or "tcp").lower(),
            "sni": str(obj.get("sni", "") or obj.get("host", "")),
            "flow": "",
            "tag": tag,
        }
        node["country"] = guess_country(tag + " " + host)
        return node
    except Exception:
        return None


def parse_trojan(link):
    try:
        body = link[len("trojan://"):]
        tag = ""
        if "\u0023" in body:
            body, frag = body.split("\u0023", 1)
            tag = urllib.parse.unquote(frag)
        if "@" not in body:
            return None
        pwd, hostinfo = body.rsplit("@", 1)
        pwd = urllib.parse.unquote(pwd)
        if "?" in hostinfo:
            hostport, query = hostinfo.split("?", 1)
        else:
            hostport, query = hostinfo, ""
        if ":" in hostport:
            host, port = hostport.rsplit(":", 1)
        else:
            host, port = hostport, "443"
        host = host.strip()
        try:
            port = int(str(port).strip())
        except Exception:
            return None
        q = urllib.parse.parse_qs(query, keep_blank_values=True)
        def one(k, d=""):
            v = q.get(k, [d])
            return v[0] if v else d
        node = {
            "raw": link,
            "proto": "trojan",
            "id": pwd,
            "host": host,
            "port": port,
            "security": (one("security", "tls") or "tls").lower(),
            "transport": (one("type", "tcp") or "tcp").lower(),
            "sni": one("sni", one("host", "")),
            "flow": one("flow", ""),
            "tag": clean_tag(tag) or (host + ":" + str(port)),
        }
        node["country"] = guess_country(node["tag"] + " " + host)
        return node
    except Exception:
        return None


def parse_ss(link):
    try:
        body = link[len("ss://"):]
        tag = ""
        if "\u0023" in body:
            body, frag = body.split("\u0023", 1)
            tag = urllib.parse.unquote(frag)
        host = ""
        port = 0
        ident = body
        if "@" in body:
            left, right = body.rsplit("@", 1)
            if ":" in right:
                host, p = right.rsplit(":", 1)
                p = p.split("?", 1)[0].split("/", 1)[0]
                try:
                    port = int(p.strip())
                except Exception:
                    port = 0
                host = host.strip()
            if ":" in left and len(left) < 200:
                ident = left
            else:
                try:
                    pad = left + ("=" * (-len(left) % 4))
                    ident = base64.b64decode(pad).decode("utf-8", errors="strict")
                except Exception:
                    ident = left
        else:
            core = body.split("?", 1)[0].split("/", 1)[0]
            try:
                pad = core + ("=" * (-len(core) % 4))
                dec = base64.b64decode(pad).decode("utf-8", errors="strict")
                if "@" in dec and ":" in dec:
                    left, right = dec.rsplit("@", 1)
                    ident = left
                    if ":" in right:
                        host, p = right.rsplit(":", 1)
                        try:
                            port = int(p.strip())
                        except Exception:
                            port = 0
            except Exception:
                return None
        if not host or not port:
            return None
        node = {
            "raw": link,
            "proto": "ss",
            "id": ident,
            "host": host,
            "port": port,
            "security": "none",
            "transport": "tcp",
            "sni": "",
            "flow": "",
            "tag": clean_tag(tag) or (host + ":" + str(port)),
        }
        node["country"] = guess_country(node["tag"] + " " + host)
        return node
    except Exception:
        return None


def parse_generic(link):
    try:
        for prefix in ("hysteria2://", "hy2://", "tuic://", "vless://", "vmess://", "trojan://", "ss://"):
            if link.startswith(prefix):
                break
        m = re.search(r"@([^/:?]+):(\d+)", link)
        if not m:
            m = re.search(r"://([^/:?]+):(\d+)", link)
        if not m:
            return None
        host = m.group(1)
        port = int(m.group(2))
        proto = link.split("://", 1)[0].lower()
        if proto == "hy2":
            proto = "hysteria2"
        tag = host + ":" + str(port)
        if "\u0023" in link:
            frag = link.rsplit("\u0023", 1)[1]
            tag = clean_tag(urllib.parse.unquote(frag)) or tag
        node = {
            "raw": link,
            "proto": proto,
            "id": proto,
            "host": host,
            "port": port,
            "security": "tls",
            "transport": "udp",
            "sni": "",
            "flow": "",
            "tag": tag,
        }
        node["country"] = guess_country(tag + " " + host)
        return node
    except Exception:
        return None


def parse_link(link):
    s = (link or "").strip()
    if s.startswith("vless://"):
        return parse_vless(s)
    if s.startswith("vmess://"):
        return parse_vmess(s)
    if s.startswith("trojan://"):
        return parse_trojan(s)
    if s.startswith("ss://"):
        return parse_ss(s)
    if s.startswith("hysteria2://") or s.startswith("hy2://") or s.startswith("tuic://"):
        return parse_generic(s)
    return None


def dedupe(nodes):
    seen = set()
    out = []
    for n in nodes:
        if not n:
            continue
        q = (n.get("raw", "") or "")
        path = ""
        try:
            if "?" in q:
                path = q.split("?", 1)[1].split("\u0023", 1)[0][:80]
        except Exception:
            path = ""
        key = "|".join([
            str(n.get("proto", "")),
            str(n.get("id", "")),
            str(n.get("host", "")).lower(),
            str(n.get("port", "")),
            str(n.get("security", "")),
            str(n.get("transport", "")),
            path,
        ])
        if key in seen:
            continue
        seen.add(key)
        out.append(n)
    return out


def parse_all(links):
    nodes = []
    for link in links:
        n = parse_link(link)
        if n:
            nodes.append(n)
    nodes = dedupe(nodes)
    vless = [n for n in nodes if n.get("proto") == "vless"]
    rest = [n for n in nodes if n.get("proto") != "vless"]
    return vless + rest
