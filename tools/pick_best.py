import asyncio
import re
import sys
import httpx
from src.parse import parse_all
from src.util import decode_bytes, maybe_b64_to_text, split_links
from src.check import tcp_rtt


URL = "https://raw.githubusercontent.com/lumskyy/LumoVessConfig/main/output/happ-all.txt"
NEAR = {"RU", "PL", "FI", "DE", "NL", "SE", "UA", "BY", "KZ", "TR", "EE", "LV", "LT", "RO", "CZ", "AT", "CH", "FR", "GB", "IE", "IT", "ES", "PT", "GR", "HU", "RS", "HR", "BG", "MD", "GE", "AM", "AZ"}


def tag_ms(tag):
    m = re.search(r"(\d+)\s*ms", tag or "")
    return int(m.group(1)) if m else 9999


async def main(url, top=15):
    async with httpx.AsyncClient(headers={"User-Agent": "LumoVessConfig/1.0"}, follow_redirects=True) as c:
        r = await c.get(url, timeout=40)
        text = decode_bytes(r.content)
    links = split_links(maybe_b64_to_text(text))
    nodes = parse_all(links)
    print("fetched_links " + str(len(links)) + " parsed_nodes " + str(len(nodes)))
    vr = [n for n in nodes if n.get("proto") == "vless" and str(n.get("security", "") or "").lower() == "reality"]
    print("reality_nodes " + str(len(vr)))
    vr.sort(key=lambda n: (0 if str(n.get("country", "UN")).upper() in NEAR else 1, tag_ms(n.get("tag", ""))))
    cand = vr[:top]
    sem = asyncio.Semaphore(8)

    async def probe(n):
        async with sem:
            v = await tcp_rtt(str(n.get("host", "")), int(n.get("port", 443)), timeout=6)
            return n, v

    res = await asyncio.gather(*[probe(n) for n in cand])
    scored = []
    for n, v in res:
        if v is not None:
            scored.append((v, tag_ms(n.get("tag", "")), n))
    scored.sort(key=lambda t: (t[0], t[1]))
    for v, listed, n in scored[:5]:
        print(str(int(v)) + "ms_here " + str(listed) + "ms_listed " + str(n.get("country", "UN")) + " " + str(n.get("host", "")) + ":" + str(n.get("port", "")))
    if scored:
        print("WINNER_RAW:")
        print(scored[0][2].get("raw", ""))
    else:
        print("NO_WINNER")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else URL))
