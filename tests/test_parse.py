from src.parse import parse_link, dedupe, guess_country
from src.rank import pick_elite
import struct


def test_vless_basic():
    link = "vless://11111111-2222-3333-4444-555555555555@203.0.113.10:443?security=reality&type=tcp&flow=xtls-rprx-vision&sni=www.microsoft.com&fp=chrome&pbk=abc&sid=01\u0023JP-Tokyo-01"
    n = parse_link(link)
    assert n is not None
    assert n["proto"] == "vless"
    assert n["host"] == "203.0.113.10"
    assert n["port"] == 443
    assert n["country"] == "JP"


def test_dedupe_drops_repeat():
    a = parse_link("vless://11111111-2222-3333-4444-555555555555@203.0.113.10:443?type=tcp&security=none\u0023a")
    b = parse_link("vless://11111111-2222-3333-4444-555555555555@203.0.113.10:443?type=tcp&security=none\u0023b")
    out = dedupe([a, b])
    assert len(out) == 1


def test_flags_and_aliases():
    assert guess_country("Poland 🇵🇱 Warsaw node") == "PL"
    assert guess_country("Polska serwer 12") == "PL"
    assert guess_country("Россия МСК") == "RU"
    assert guess_country("Украина Киев") == "UA"
    assert guess_country("🇺🇦 Kyiv 03") == "UA"
    assert guess_country("美国 $") == "US"


def test_elite_keeps_stable_only():
    good = (10, {"node": {"host": "1.1.1.1", "port": 443, "id": "a", "country": "PL", "proto": "vless", "security": "reality"}, "rounds_ok": 3, "leak": False, "full": True, "exit_ip": "9.9.9.9", "google": 2, "cf": 1, "tcp_ms": 120, "http_ms": 300, "tcp_spread": 40, "http_spread": 90, "udp_ms": 200, "udp_spread": 50, "udp_ok": 3})
    shaky = (99, {"node": {"host": "2.2.2.2", "port": 443, "id": "b", "country": "DE", "proto": "vless", "security": "reality"}, "rounds_ok": 3, "leak": False, "full": True, "exit_ip": "8.8.8.8", "google": 2, "cf": 1, "tcp_ms": 100, "http_ms": 250, "tcp_spread": 900, "http_spread": 90, "udp_ms": 200, "udp_spread": 50, "udp_ok": 3})
    leaked = (99, {"node": {"host": "3.3.3.3", "port": 443, "id": "c", "country": "NL", "proto": "vless"}, "rounds_ok": 3, "leak": True, "full": True, "exit_ip": "7.7.7.7", "google": 2, "cf": 1, "tcp_ms": 90, "http_ms": 200, "tcp_spread": 10, "http_spread": 10})
    out = pick_elite([shaky, leaked, good], 3, True)
    assert len(out) == 1
    assert out[0][1]["node"]["host"] == "1.1.1.1"


def test_rejects_lines_with_spaces():
    assert parse_link("5 @user hysteria2://abc@1.2.3.4:443#tag") is None
    assert parse_link("vless://11111111-2222-3333-4444-555555555555@203.0.113.10:443?type=tcp&a=b c") is None
    assert parse_link("just some words :// nothing") is None


def test_tag_with_scheme_gets_replaced():
    n = parse_link("vless://11111111-2222-3333-4444-555555555555@203.0.113.10:443?type=tcp&security=none" + "\u0023AAA://BBB")
    assert n is not None
    assert n["tag"] == "203.0.113.10:443"


def test_generic_parses_strict():
    n = parse_link("hy2://secret@1.2.3.4:443#Nice")
    assert n is not None
    assert n["host"] == "1.2.3.4"
    assert n["port"] == 443
    assert n["proto"] == "hysteria2"


def test_dns_packet_roundtrip():
    from src.check import build_dns_query, parse_dns_ok
    txid, pkt = build_dns_query()
    assert len(pkt) > 12
    answer = struct.pack(">HHHHHH", txid, 0x8180, 1, 1, 0, 0) + pkt[12:] + b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04\x08\x08\x08\x08"
    assert parse_dns_ok(answer, txid) is True
    assert parse_dns_ok(answer, txid + 1) is False
    assert parse_dns_ok(b"\x00\x01", txid) is False


def test_elite_needs_udp_and_vless_tls():
    base = {"rounds_ok": 3, "leak": False, "full": True, "exit_ip": "9.9.9.9", "google": 2, "cf": 1, "tcp_ms": 120, "http_ms": 300, "tcp_spread": 40, "http_spread": 90, "udp_ms": 200, "udp_spread": 50, "udp_ok": 3}
    good = (10, dict(base, node={"host": "1.1.1.1", "port": 443, "id": "a", "country": "PL", "proto": "vless", "security": "reality"}))
    no_udp = (99, dict(base, udp_ok=0, udp_ms=0, node={"host": "2.2.2.2", "port": 443, "id": "b", "country": "DE", "proto": "vless", "security": "reality"}))
    plain = (99, dict(base, node={"host": "3.3.3.3", "port": 443, "id": "c", "country": "NL", "proto": "ss", "security": "none"}))
    out = pick_elite([no_udp, plain, good], 3, True)
    assert len(out) == 1
    assert out[0][1]["node"]["host"] == "1.1.1.1"


def test_pretty_name_extra():
    from src.emit import pretty_name
    assert pretty_name("best", "DE", 1, 168, "vless", "Reality+Vision") == "⭐ BEST · Germany · 01 · 168ms · VLESS Reality+Vision"
    assert pretty_name("std", "JP", 4, 182, "vless", "") == "Japan · 04 · 182ms · VLESS"


def test_best_needs_signal_in_full_mode():
    from src.rank import pick_best
    slow = (5, {"node": {"host": "1.1.1.1", "port": 443, "id": "a"}, "udp_ok": 0, "http_ms": 900})
    quick = (10, {"node": {"host": "2.2.2.2", "port": 443, "id": "b"}, "udp_ok": 0, "http_ms": 200})
    assert pick_best([slow, quick], True) == [quick]
    assert pick_best([slow, quick], False) == [slow, quick]


def test_gaming_needs_udp_in_full_mode():
    from src.rank import pick_gaming
    mute = (5, {"node": {"host": "1.1.1.1", "port": 443, "id": "a", "proto": "vless", "country": "US"}, "tcp_ms": 100, "rounds_ok": 3, "udp_ok": 0})
    live = (4, {"node": {"host": "2.2.2.2", "port": 443, "id": "b", "proto": "vless", "country": "US"}, "tcp_ms": 200, "rounds_ok": 3, "udp_ok": 2})
    assert pick_gaming([mute, live], True) == [live]
    assert pick_gaming([mute, live], False) == [live, mute]


def test_rank_all_full_suite():
    from src.rank import rank_all
    ok_node = {"node": {"host": "1.1.1.1", "port": 443, "id": "a", "country": "PL", "proto": "vless", "security": "reality"}, "rounds_ok": 3, "leak": False, "full": True, "exit_ip": "9.9.9.9", "google": 1, "cf": 1, "tcp_ms": 120, "http_ms": 300, "tcp_spread": 40, "http_spread": 90, "udp_ms": 200, "udp_spread": 50, "udp_ok": 2}
    no_udp = dict(ok_node, udp_ok=0, udp_ms=0)
    no_cf = dict(ok_node, cf=0)
    tcp_only = dict(ok_node, full=False, google=0, cf=0, udp_ok=0, http_ms=0)
    alive, has_full = rank_all([no_udp, no_cf, tcp_only, ok_node])
    assert has_full is True
    assert [x["node"]["host"] for _, x in alive] == ["1.1.1.1"]
