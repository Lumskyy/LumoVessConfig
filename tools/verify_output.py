import base64
import json
import os
import sys
import urllib.parse
import yaml
from src.parse import parse_link


def check_list(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    bad_char = "�" in content
    lines = [x for x in content.splitlines() if x.strip()]
    noproto = 0
    noparse = 0
    noname = 0
    for line in lines:
        if "://" not in line:
            noproto = noproto + 1
            continue
        if parse_link(line) is None:
            noparse = noparse + 1
        if "#" not in line:
            noname = noname + 1
            continue
        frag = line.rsplit("#", 1)[1]
        try:
            name = urllib.parse.unquote(frag)
        except Exception:
            name = ""
        if not name.strip():
            noname = noname + 1
    return {"lines": len(lines), "bad_char": bad_char, "noproto": noproto, "noparse": noparse, "noname": noname}


def main():
    ok = True
    base = "output"
    for name in ["happ-elite.txt", "happ-best.txt", "happ-gaming.txt", "happ-all.txt", "happ-vless.txt"]:
        r = check_list(os.path.join(base, name))
        print(name + " " + json.dumps(r, ensure_ascii=True))
        if r["lines"] == 0 or r["bad_char"] or r["noproto"] or r["noname"]:
            ok = False
    cdir = os.path.join(base, "countries")
    files = sorted([x for x in os.listdir(cdir) if x.endswith(".txt")])
    print("countries_files " + str(len(files)))
    total = 0
    for fn in files:
        r = check_list(os.path.join(cdir, fn))
        total = total + r["lines"]
        if r["lines"] == 0 or r["bad_char"] or r["noproto"]:
            ok = False
            print("BAD " + fn + " " + json.dumps(r, ensure_ascii=True))
    print("countries_lines " + str(total))
    with open(os.path.join(base, "v2ray.txt"), encoding="utf-8") as f:
        blob = f.read().strip()
    raw = base64.b64decode(blob).decode("utf-8")
    vlines = [x for x in raw.splitlines() if x.strip()]
    vparse = sum(1 for x in vlines if parse_link(x) is not None)
    print("v2ray lines " + str(len(vlines)) + " parsed " + str(vparse))
    if not vlines:
        ok = False
    with open(os.path.join(base, "clash.yaml"), encoding="utf-8") as f:
        clash = yaml.safe_load(f)
    print("clash proxies " + str(len(clash.get("proxies", []))) + " groups " + str(len(clash.get("proxy-groups", []))))
    if not clash.get("proxies"):
        ok = False
    with open(os.path.join(base, "singbox.json"), encoding="utf-8") as f:
        box = json.load(f)
    print("singbox outbounds " + str(len(box.get("outbounds", []))))
    if not box.get("outbounds"):
        ok = False
    with open(os.path.join(base, "stats.json"), encoding="utf-8") as f:
        stats = json.load(f)
    counts = {}
    for name in ["happ-elite.txt", "happ-best.txt", "happ-gaming.txt", "happ-all.txt"]:
        with open(os.path.join(base, name), encoding="utf-8") as f:
            counts[name] = len([x for x in f.read().splitlines() if x.strip()])
    match = (counts["happ-all.txt"] == stats["alive"] and counts["happ-best.txt"] == stats["best"] and counts["happ-elite.txt"] == stats["elite"] and counts["happ-gaming.txt"] == stats["gaming"] and len(files) == stats["countries"])
    print("stats_match " + str(match) + " " + json.dumps(counts, ensure_ascii=True))
    if not match:
        ok = False
    print("RESULT " + ("OK" if ok else "FAIL"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
