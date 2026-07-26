#!/usr/bin/env python3
"""Generate Karing diversion + sing-box rulesets from clash.ini (full ruleset list)."""

from __future__ import annotations

import json
import urllib.request
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
OUT_RS = OUT / "ruleset"
BASE = "https://raw.githubusercontent.com/yywill/clash_rules/main/karing/ruleset"

LOCAL_MAP = {
    "https://raw.githubusercontent.com/yywill/clash_rules/main/Direct.list": ROOT
    / "Direct.list",
    "https://raw.githubusercontent.com/yywill/clash_rules/main/ProxyLite.list": ROOT
    / "ProxyLite.list",
    "https://raw.githubusercontent.com/yywill/clash_rules/main/AI.list": ROOT / "AI.list",
    "https://raw.githubusercontent.com/yywill/clash_rules/main/nostr.list": ROOT
    / "nostr.list",
    "https://raw.githubusercontent.com/yywill/clash_rules/main/work.list": ROOT
    / "work.list",
    "https://raw.githubusercontent.com/yywill/clash_rules/main/GitHub.list": ROOT
    / "GitHub.list",
}

DEFAULT_OUTBOUND = {
    "🎯 全球直连": "direct",
    "🗑 字节网站": "direct",
    "🟢 微信": "direct",
    "🎞️ 国内媒体": "direct",
    "🍎 Apple": "direct",
    "♻️ Speedtest": "direct",
    "🛑 广告拦截": "block",
    "🍃 应用净化": "block",
    "🐟 漏网之鱼": "currentSelected",
    "🚀 节点选择": "currentSelected",
}


def parse_clash_ini_rulesets() -> list[tuple[str, str]]:
    text = (ROOT / "clash.ini").read_text(encoding="utf-8")
    entries: list[tuple[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("ruleset="):
            continue
        body = line[len("ruleset=") :]
        parts = body.split(",", 1)
        if len(parts) < 2:
            continue
        entries.append((parts[0].strip(), parts[1].strip()))
    return entries


def parse_clash_list(content: str) -> dict[str, list[str]]:
    domain: list[str] = []
    domain_suffix: list[str] = []
    domain_keyword: list[str] = []
    ip_cidr: list[str] = []
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 2:
            continue
        typ, val = parts[0].upper(), parts[1]
        if typ == "DOMAIN":
            domain.append(val)
        elif typ == "DOMAIN-SUFFIX":
            domain_suffix.append(val)
        elif typ == "DOMAIN-KEYWORD":
            domain_keyword.append(val)
        elif typ in ("IP-CIDR", "IP-CIDR6"):
            ip_cidr.append(val)

    def uniq(xs: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for x in xs:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    return {
        "domain": uniq(domain),
        "domain_suffix": uniq(domain_suffix),
        "domain_keyword": uniq(domain_keyword),
        "ip_cidr": uniq(ip_cidr),
    }


def fetch(url: str) -> str:
    local = LOCAL_MAP.get(url)
    if local is not None and local.exists():
        return local.read_text(encoding="utf-8")
    req = urllib.request.Request(
        url, headers={"User-Agent": "clash-rules-karing-generator"}
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read().decode("utf-8", errors="replace")


def slugify(url: str) -> str:
    path = url.split("?", 1)[0].rstrip("/")
    name = path.rsplit("/", 1)[-1]
    if name.endswith(".list"):
        name = name[: -len(".list")]
    if "/yywill/clash_rules/" in url:
        prefix = "personal"
    elif "/yywill/ACL4SSR/" in url:
        prefix = "acl"
    elif "/yywill/ios_rule_script/" in url:
        prefix = "ios"
    elif "/ACL4SSR/ACL4SSR/" in url:
        prefix = "aclup"
    elif "/blackmatrix7/ios_rule_script/" in url:
        prefix = "bm7"
    else:
        prefix = "ext"
    return f"{prefix}-{name}"


def convert_lists(entries: list[tuple[str, str]]) -> tuple[dict[str, str], list]:
    OUT_RS.mkdir(parents=True, exist_ok=True)
    # Keep existing json as download cache; remove orphans at end.
    keep_slugs: set[str] = set()

    url_to_slug: OrderedDict[str, str] = OrderedDict()
    failed: list[tuple[str, str]] = []
    used_slugs: set[str] = set()

    for _, rest in entries:
        if not rest.startswith("http"):
            continue
        url = rest
        if url in url_to_slug:
            continue
        slug = slugify(url)
        base = slug
        i = 2
        while slug in used_slugs:
            slug = f"{base}-{i}"
            i += 1

        out_path = OUT_RS / f"{slug}.json"
        content = None
        last_err = ""
        for attempt in range(3):
            try:
                content = fetch(url)
                break
            except Exception as exc:  # noqa: BLE001
                last_err = str(exc)
                if attempt < 2:
                    import time

                    time.sleep(1.5 * (attempt + 1))

        if content is None:
            if out_path.exists():
                print(f"CACHE {slug}.json (download failed: {last_err})")
                url_to_slug[url] = slug
                used_slugs.add(slug)
                keep_slugs.add(slug)
                continue
            failed.append((url, last_err))
            print(f"FAIL {url}: {last_err}")
            continue

        parsed = parse_clash_list(content)
        rule = {k: v for k, v in parsed.items() if v}
        data = {"version": 2, "rules": [rule] if rule else []}
        out_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        url_to_slug[url] = slug
        used_slugs.add(slug)
        keep_slugs.add(slug)
        n = sum(len(v) for v in parsed.values())
        print(f"OK {slug}.json ({n} items)")

    for old in OUT_RS.glob("*.json"):
        if old.stem not in keep_slugs:
            old.unlink()

    return dict(url_to_slug), failed


def build_rules(
    entries: list[tuple[str, str]], url_to_slug: dict[str, str]
) -> list[dict]:
    """Preserve clash.ini order. Only merge *consecutive* same-name rulesets.

    Non-consecutive repeats (e.g. early XboxCDN 全球直连 vs late ChinaDomain
    全球直连) become separate groups so late catch-alls cannot steal priority.
    """

    rules: list[dict] = []
    name_counts: dict[str, int] = {}
    current: dict | None = None
    current_base: str | None = None

    def flush() -> None:
        nonlocal current
        if not current:
            return
        if not current.get("rule_set") and not current.get("rule_set_build_in"):
            current = None
            return
        r: dict = {
            "name": current["name"],
            "outbound": current["outbound"],
            "switch": True,
        }
        if current["rule_set"]:
            r["rule_set"] = current["rule_set"]
        if current["rule_set_build_in"]:
            r["rule_set_build_in"] = current["rule_set_build_in"]
        rules.append(r)
        current = None

    def start_group(base_name: str) -> dict:
        nonlocal current, current_base
        flush()
        count = name_counts.get(base_name, 0) + 1
        name_counts[base_name] = count
        display = base_name if count == 1 else f"{base_name} ·{count}"
        current_base = base_name
        current = {
            "name": display,
            "outbound": DEFAULT_OUTBOUND.get(base_name, "currentSelected"),
            "rule_set": [],
            "rule_set_build_in": [],
        }
        return current

    for name, rest in entries:
        if current is None or current_base != name:
            g = start_group(name)
        else:
            g = current
            assert g is not None

        if rest.startswith("http"):
            slug = url_to_slug.get(rest)
            if not slug:
                continue
            url = f"{BASE}/{slug}.json"
            if url not in g["rule_set"]:
                g["rule_set"].append(url)
        elif rest.startswith("[]GEOSITE,"):
            code = rest.split(",", 1)[1].strip()
            tag = f"geosite:{code}"
            if tag not in g["rule_set_build_in"]:
                g["rule_set_build_in"].append(tag)
        elif rest.startswith("[]GEOIP,"):
            code = rest.split(",")[1].strip()
            tag = f"geoip:{code}"
            if tag not in g["rule_set_build_in"]:
                g["rule_set_build_in"].append(tag)
        elif rest.startswith("[]FINAL"):
            # unmatched traffic uses Karing default; no matcher to add
            pass

    flush()

    # Match Surge priority: ByteDance / WeChat must be before broad China/proxy lists.
    priority_prefix = ("🗑 字节网站", "🟢 微信")
    head = [r for r in rules if r["name"].startswith(priority_prefix)]
    tail = [r for r in rules if not r["name"].startswith(priority_prefix)]
    return head + tail


def write_runtime(rules: list[dict]) -> None:
    groups = []
    diversion_use = []
    rule_set_items = []
    seen: set[str] = set()
    for idx, r in enumerate(rules):
        g: dict = {
            "groupid": "custom",
            "name": r["name"],
            "type": "",
            "or": True,
            "index": idx,
        }
        for key in ("rule_set_build_in", "rule_set"):
            if key in r:
                g[key] = r[key]
        if "rule_set" in r:
            for url in r["rule_set"]:
                if url in seen:
                    continue
                seen.add(url)
                rule_set_items.append(
                    {
                        "type": "remote",
                        "tag": url,
                        "format": "source" if url.endswith(".json") else "binary",
                        "url": url,
                        "download_detour": "",
                        "update_interval": 86400,
                    }
                )
        groups.append(g)
        outbound = r["outbound"]
        if outbound == "direct":
            diversion_use.append(
                {
                    "diversion_groupid": "custom",
                    "diversion_name": r["name"],
                    "server_groupid": "direct",
                    "server_name": "direct_out",
                    "dns_servers": [],
                }
            )
        elif outbound == "block":
            diversion_use.append(
                {
                    "diversion_groupid": "custom",
                    "diversion_name": r["name"],
                    "server_groupid": "block",
                    "server_name": "block_out",
                    "dns_servers": [],
                }
            )
        else:
            diversion_use.append(
                {
                    "diversion_groupid": "custom",
                    "diversion_name": r["name"],
                    "server_groupid": "currentSelected",
                    "server_name": "",
                    "dns_servers": [],
                }
            )

    routing = {
        "items": [
            {
                "groupid": "custom",
                "urlOrPath": "",
                "remark": "",
                "editAble": True,
                "groups": groups,
            }
        ],
        "rule_set_items": rule_set_items,
    }
    (OUT / "karing_routing_group.json").write_text(
        json.dumps(routing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "karing_subscribe_use.diversion.json").write_text(
        json.dumps({"diversion_group": diversion_use}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )


def apply_local(rules: list[dict], routing_path: Path | None = None) -> None:
    """Apply to local Karing app config, inlining ruleset JSON so it works pre-push."""
    karing = Path.home() / "Library/Group Containers/group.com.nebula.karing"
    if not karing.exists():
        print("skip local apply: Karing data dir not found")
        return

    rulesets: dict[str, dict] = {}
    for p in OUT_RS.glob("*.json"):
        data = json.loads(p.read_text(encoding="utf-8"))
        rule = data["rules"][0] if data.get("rules") else {}
        rulesets[p.stem] = rule

    routing = json.loads((OUT / "karing_routing_group.json").read_text(encoding="utf-8"))
    for item in routing["items"]:
        for g in item["groups"]:
            for url in g.get("rule_set", []):
                slug = url.rsplit("/", 1)[-1].removesuffix(".json")
                rs = rulesets.get(slug)
                if not rs:
                    continue
                for key in ("domain", "domain_suffix", "domain_keyword", "ip_cidr"):
                    if not rs.get(key):
                        continue
                    existing = list(g.get(key, []))
                    seen = set(existing)
                    for v in rs[key]:
                        if v not in seen:
                            existing.append(v)
                            seen.add(v)
                    g[key] = existing

    (karing / "karing_routing_group.json").write_text(
        json.dumps(routing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    use_path = karing / "karing_subscribe_use.json"
    use = json.loads(use_path.read_text(encoding="utf-8"))
    div = json.loads(
        (OUT / "karing_subscribe_use.diversion.json").read_text(encoding="utf-8")
    )
    use["diversion_group"] = div["diversion_group"]
    use_path.write_text(json.dumps(use, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    setting_path = karing / "karing_setting.json"
    setting = json.loads(setting_path.read_text(encoding="utf-8"))
    setting["region_code"] = "CN"
    rs = setting.setdefault("rule_sets", {})
    rs["disable_custom_diversion_group"] = False
    rs["disable_isp_diversion_group"] = True
    rs["enable_geosite"] = True
    rs["enable_geoip"] = True
    rs["enable_acl"] = True
    setting_path.write_text(
        json.dumps(setting, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"applied local Karing: groups={len(routing['items'][0]['groups'])} "
        f"remote={len(routing['rule_set_items'])}"
    )


def main() -> None:
    entries = parse_clash_ini_rulesets()
    print(f"clash.ini ruleset lines: {len(entries)}")
    url_to_slug, failed = convert_lists(entries)
    rules = build_rules(entries, url_to_slug)

    (OUT / "diversion_rules_custom.json").write_text(
        json.dumps({"rules": rules}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_runtime(rules)
    (OUT / "ruleset_sources.json").write_text(
        json.dumps(
            {
                "url_to_slug": url_to_slug,
                "failed": failed,
                "groups": [r["name"] for r in rules],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print("\n=== GROUPS ===")
    for r in rules:
        print(
            f"  [{r['outbound']:16}] {r['name']}  "
            f"remote={len(r.get('rule_set', []))} "
            f"builtin={len(r.get('rule_set_build_in', []))}"
        )
    rs_count = len(list(OUT_RS.glob("*.json")))
    print(f"\nwrote diversion_rules_custom.json ({len(rules)} groups)")
    print(f"ruleset json files: {rs_count}")
    if failed:
        print(f"FAILED downloads: {len(failed)}")
        for url, err in failed:
            print(f"  {url}: {err}")

    apply_local(rules)


if __name__ == "__main__":
    main()
