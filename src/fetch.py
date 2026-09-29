import asyncio
import httpx
from src.util import decode_bytes, maybe_b64_to_text, split_links


HEADERS = {
    "User-Agent": "LumoVessConfig/1.0",
    "Accept": "text/plain,*/*",
}


async def fetch_one(client, url, timeout=30):
    try:
        r = await client.get(url, timeout=timeout, follow_redirects=True)
        if r.status_code != 200:
            return url, []
        text = decode_bytes(r.content)
        text = maybe_b64_to_text(text)
        if "://" not in text and len(text) > 100:
            try:
                import base64
                parts = []
                for line in text.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        pad = line + ("=" * (-len(line) % 4))
                        parts.append(base64.b64decode(pad).decode("utf-8", errors="strict"))
                    except Exception:
                        parts.append(line)
                text = "\n".join(parts)
            except Exception:
                pass
        links = split_links(text)
        return url, links
    except Exception:
        return url, []


async def fetch_all(urls, limit=8, timeout=30):
    results = {}
    ok = 0
    async with httpx.AsyncClient(headers=HEADERS, http2=False) as client:
        sem = asyncio.Semaphore(limit)

        async def bound(u):
            async with sem:
                return await fetch_one(client, u, timeout)

        tasks = [bound(u) for u in urls]
        for item in await asyncio.gather(*tasks):
            url, links = item
            results[url] = links
            if links:
                ok = ok + 1
    flat = []
    for u in urls:
        flat.extend(results.get(u, []))
    return flat, results, ok
