from src.parse import parse_link, dedupe, guess_country
from src.rank import pick_elite


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
    good = (10, {"node": {"host": "1.1.1.1", "port": 443, "id": "a", "country": "PL", "proto": "vless"}, "rounds_ok": 3, "leak": False, "full": True, "exit_ip": "9.9.9.9", "google": 2, "cf": 1, "tcp_ms": 120, "http_ms": 300, "tcp_spread": 40, "http_spread": 90})
    shaky = (99, {"node": {"host": "2.2.2.2", "port": 443, "id": "b", "country": "DE", "proto": "vless"}, "rounds_ok": 3, "leak": False, "full": True, "exit_ip": "8.8.8.8", "google": 2, "cf": 1, "tcp_ms": 100, "http_ms": 250, "tcp_spread": 900, "http_spread": 90})
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
