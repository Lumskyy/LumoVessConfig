import asyncio
import sys
import httpx
from src.util import maybe_b64_to_text, split_links


async def check_one(client, url):
    try:
        r = await client.get(url, timeout=25, follow_redirects=True)
        n = 0
        if r.status_code == 200:
            try:
                t = r.content.decode("utf-8", errors="strict")
            except Exception:
                t = ""
            n = len(split_links(maybe_b64_to_text(t)))
        print(url + " | " + str(r.status_code) + " | " + str(n))
    except Exception as e:
        print(url + " | ERR | " + type(e).__name__)


async def main(urls):
    async with httpx.AsyncClient(headers={"User-Agent": "LumoVessConfig/1.0"}) as c:
        for u in urls:
            await check_one(c, u)


if __name__ == "__main__":
    main_urls = sys.argv[1:]
    asyncio.run(main(main_urls))
