import asyncio
import os
from src.sources import SOURCES
from src.fetch import fetch_all
from src.parse import parse_all
from src.check import triple_check
from src.rank import rank_all, pick_best, pick_elite, pick_gaming, group_countries, finalize
from src.emit import ensure_dirs, rename_list, write_all, build_stats


async def main():
    ensure_dirs()
    rounds = int(os.environ.get("LUMO_ROUNDS", "3"))
    delay = int(os.environ.get("LUMO_DELAY", "25"))
    prefilter = int(os.environ.get("LUMO_PREFILTER", "1400"))
    flat, _, ok = await fetch_all(SOURCES, limit=8, timeout=30)
    total_in = len(flat)
    nodes = parse_all(flat)
    parsed = len(nodes)
    maxin = int(os.environ.get("LUMO_MAXIN", "3000"))
    if maxin > 0:
        nodes = nodes[:maxin]
    if not nodes:
        stats = build_stats(total_in, parsed, 0, [], [], [], [], {}, ok, len(SOURCES), False)
        write_all([], [], [], {}, [], stats)
        return
    checked = await triple_check(nodes, rounds=rounds, delay=delay, prefilter=prefilter, limit=64)
    alive, has_full = rank_all(checked)
    best_pairs = pick_best(alive, limit=120)
    elite_pairs = pick_elite(alive, rounds, has_full, limit=80, per_country=8)
    game_pairs = pick_gaming(alive, limit=150)
    groups = group_countries(alive, per=40)
    best_keys = finalize(best_pairs, alive)
    elite_keys = finalize(elite_pairs, alive)
    best = rename_list(best_pairs, kind_mode="best")
    elite = rename_list(elite_pairs, kind_mode="elite")
    game_keys = set()
    gaming = []
    for s, x in game_pairs:
        n = x.get("node", {})
        k = str(n.get("host", "")).lower() + ":" + str(n.get("port", "")) + ":" + str(n.get("id", ""))[:12]
        if k in best_keys:
            continue
        if k in game_keys:
            continue
        game_keys.add(k)
        gaming.append((s, x))
    gaming = rename_list(gaming, kind_mode="game")
    rest = []
    seen = set()
    for s, x in elite_pairs:
        n = x.get("node", {})
        k = str(n.get("host", "")).lower() + ":" + str(n.get("port", "")) + ":" + str(n.get("id", ""))[:12]
        seen.add(k)
    for s, x in best_pairs:
        n = x.get("node", {})
        k = str(n.get("host", "")).lower() + ":" + str(n.get("port", "")) + ":" + str(n.get("id", ""))[:12]
        seen.add(k)
    for s, x in game_pairs:
        n = x.get("node", {})
        k = str(n.get("host", "")).lower() + ":" + str(n.get("port", "")) + ":" + str(n.get("id", ""))[:12]
        seen.add(k)
    tail = []
    for s, x in alive:
        n = x.get("node", {})
        k = str(n.get("host", "")).lower() + ":" + str(n.get("port", "")) + ":" + str(n.get("id", ""))[:12]
        if k in seen:
            continue
        tail.append((s, x))
    ordered_pairs = list(elite_pairs) + [p for p in best_pairs if (str(p[1].get("node", {}).get("host", "")).lower() + ":" + str(p[1].get("node", {}).get("port", "")) + ":" + str(p[1].get("node", {}).get("id", ""))[:12]) not in elite_keys] + [p for p in game_pairs if (str(p[1].get("node", {}).get("host", "")).lower() + ":" + str(p[1].get("node", {}).get("port", "")) + ":" + str(p[1].get("node", {}).get("id", ""))[:12]) not in best_keys and (str(p[1].get("node", {}).get("host", "")).lower() + ":" + str(p[1].get("node", {}).get("port", "")) + ":" + str(p[1].get("node", {}).get("id", ""))[:12]) not in elite_keys] + tail
    ordered_pairs = ordered_pairs[:800]
    tail_items = rename_list(tail, kind_mode="std")
    all_items = []
    seen_nodes = set()
    for it in elite + best + gaming + tail_items:
        n = it["node"]
        k = str(n.get("host", "")).lower() + ":" + str(n.get("port", "")) + ":" + str(n.get("id", ""))[:12]
        if k in seen_nodes:
            continue
        seen_nodes.add(k)
        all_items.append(it)
    all_items = all_items[:800]
    stats = build_stats(total_in, parsed, len(checked), alive, best, elite, gaming, groups, ok, len(SOURCES), has_full)
    write_all(best, elite, gaming, groups, all_items, stats)


if __name__ == "__main__":
    asyncio.run(main())
