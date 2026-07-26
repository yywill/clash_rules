#!/usr/bin/env python3
"""Generate Karing diversion + sing-box rulesets from surge.conf [Rule]."""

from __future__ import annotations

import json
import time
import urllib.request
from collections import OrderedDict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
OUT_RS = OUT / "ruleset"
BASE = "https://raw.githubusercontent.com/yywill/clash_rules/main/karing/ruleset"
SURGE_CONF = ROOT / "surge.conf"

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
    "https://raw.githubusercontent.com/yywill/clash_rules/main/FeishuLark.list": ROOT
    / "FeishuLark.list",
}

# Default Karing outbound = first option in surge.conf [Proxy Group] select lists.

AI_PROCESS_NAMES = [
    "agy",
    "Antigravity",
    "Antigravity Helper",
    "Antigravity Helper (GPU)",
    "Antigravity Helper (Plugin)",
    "Antigravity Helper (Renderer)",
    "language_server",
    "Cursor",
    "Cursor Helper",
    "Cursor Helper (GPU)",
    "Cursor Helper (Plugin)",
    "Cursor Helper (Renderer)",
    "Claude",
    "ChatGPT",
]


DEFAULT_OUTBOUND = {
    "DIRECT": "direct",
    "🖥 进程直连": "direct",
    "🎯 全球直连": "direct",
    "🗑 字节网站": "direct",
    "🟢 微信": "direct",
    "🌏 国内媒体": "direct",
    "📺 哔哩哔哩": "direct",
    "🍎 苹果服务": "direct",
    "Ⓜ️ 微软云盘": "direct",
    "Ⓜ️ 微软服务": "direct",
    "📢 谷歌FCM": "direct",
    "🎶 网易音乐": "direct",
    "🛑 广告拦截": "block",
    "🍃 应用净化": "block",
    "🐟 漏网之鱼": "currentSelected",
    "🚀 节点选择": "currentSelected",
    "🎮 游戏平台": "currentSelected",
    "💬 OpenAi": "currentSelected",
    "💧 Copilot": "currentSelected",
    "🤖 AI": "currentSelected",
    "🤖 Nostr": "currentSelected",
    "👨🏿‍💻 GitHub": "currentSelected",
    "🪙 Crypto": "currentSelected",
    "🎵 TikTok": "currentSelected",
    "📹 油管视频": "currentSelected",
    "🎥 奈飞视频": "currentSelected",
    "🍃 Google": "currentSelected",
    "🍎 AppleNews": "currentSelected",
    "🎥 DiscoveryPlus": "currentSelected",
    "🎥 MAX美国": "currentSelected",
    "🎥 HBO香港亚洲": "currentSelected",
    "🎥 PBS": "currentSelected",
    "🎵 Spotify": "currentSelected",
    "🌍 国外媒体": "currentSelected",
    "📲 Telegram": "currentSelected",
    "📲 电报消息": "currentSelected",
    "👙 porn": "currentSelected",
    "📺 巴哈姆特": "currentSelected",
}


def parse_surge_rules() -> list[dict[str, str]]:
    """Parse surge.conf [Rule] into ordered entries.

    Each entry: {kind, policy, value}
      kind=ruleset|process|geoip|ip_cidr|final
    """
    text = SURGE_CONF.read_text(encoding="utf-8")
    in_rule = False
    entries: list[dict[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            in_rule = line == "[Rule]"
            continue
        if not in_rule or not line or line.startswith("#"):
            continue

        # Strip trailing inline comments carefully — Surge rules rarely have them
        parts = [p.strip() for p in line.split(",")]
        typ = parts[0].upper()

        if typ == "RULE-SET" and len(parts) >= 3:
            url = parts[1]
            policy = parts[2]
            if policy.startswith("update-interval"):
                continue
            entries.append({"kind": "ruleset", "policy": policy, "value": url})
        elif typ == "PROCESS-NAME" and len(parts) >= 3:
            entries.append(
                {"kind": "process", "policy": parts[2], "value": parts[1]}
            )
        elif typ == "GEOIP" and len(parts) >= 3:
            entries.append({"kind": "geoip", "policy": parts[2], "value": parts[1]})
        elif typ in ("IP-CIDR", "IP-CIDR6") and len(parts) >= 3:
            entries.append({"kind": "ip_cidr", "policy": parts[2], "value": parts[1]})
        elif typ == "FINAL" and len(parts) >= 2:
            entries.append({"kind": "final", "policy": parts[1], "value": ""})
        elif typ == "DOMAIN" and len(parts) >= 3:
            entries.append({"kind": "domain", "policy": parts[2], "value": parts[1]})
        elif typ == "DOMAIN-SUFFIX" and len(parts) >= 3:
            entries.append(
                {"kind": "domain_suffix", "policy": parts[2], "value": parts[1]}
            )
        elif typ == "DOMAIN-KEYWORD" and len(parts) >= 3:
            entries.append(
                {"kind": "domain_keyword", "policy": parts[2], "value": parts[1]}
            )

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


def convert_lists(entries: list[dict[str, str]]) -> tuple[dict[str, str], list]:
    OUT_RS.mkdir(parents=True, exist_ok=True)
    keep_slugs: set[str] = set()
    url_to_slug: OrderedDict[str, str] = OrderedDict()
    failed: list[tuple[str, str]] = []
    used_slugs: set[str] = set()

    for entry in entries:
        if entry["kind"] != "ruleset":
            continue
        url = entry["value"]
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


def _group_has_matchers(g: dict[str, Any]) -> bool:
    return bool(
        g.get("rule_set")
        or g.get("rule_set_build_in")
        or g.get("processName")
        or g.get("ip_cidr")
        or g.get("domain")
        or g.get("domain_suffix")
        or g.get("domain_keyword")
    )


def build_rules(
    entries: list[dict[str, str]], url_to_slug: dict[str, str]
) -> list[dict]:
    """Preserve surge.conf [Rule] order. Merge only consecutive same policy."""

    rules: list[dict] = []
    name_counts: dict[str, int] = {}
    current: dict | None = None
    current_base: str | None = None

    def flush() -> None:
        nonlocal current
        if not current or not _group_has_matchers(current):
            current = None
            return
        r: dict = {
            "name": current["name"],
            "outbound": current["outbound"],
            "switch": True,
        }
        for key in (
            "rule_set",
            "rule_set_build_in",
            "processName",
            "ip_cidr",
            "domain",
            "domain_suffix",
            "domain_keyword",
        ):
            if current.get(key):
                r[key] = current[key]
        rules.append(r)
        current = None

    def start_group(base_name: str) -> dict:
        nonlocal current, current_base
        flush()
        # Surge PROCESS-NAME,...,DIRECT — keep separate from 全球直连 RULE-SET bands
        display_base = "🖥 进程直连" if base_name == "DIRECT" else base_name
        count = name_counts.get(display_base, 0) + 1
        name_counts[display_base] = count
        display = display_base if count == 1 else f"{display_base} ·{count}"
        current_base = base_name
        current = {
            "name": display,
            "outbound": DEFAULT_OUTBOUND.get(display_base, "currentSelected"),
            "rule_set": [],
            "rule_set_build_in": [],
            "processName": [],
            "ip_cidr": [],
            "domain": [],
            "domain_suffix": [],
            "domain_keyword": [],
        }
        return current

    for entry in entries:
        policy = entry["policy"]
        kind = entry["kind"]
        value = entry["value"]

        if kind == "final":
            # Karing unmatched traffic uses default selection; skip empty FINAL group
            continue

        if current is None or current_base != policy:
            g = start_group(policy)
        else:
            g = current
            assert g is not None

        if kind == "ruleset":
            slug = url_to_slug.get(value)
            if not slug:
                continue
            url = f"{BASE}/{slug}.json"
            if url not in g["rule_set"]:
                g["rule_set"].append(url)
        elif kind == "process":
            # Skip Surge wildcards / percent-encoded patterns Karing can't use
            if "*" in value or "%" in value or "/" in value:
                continue
            if value not in g["processName"]:
                g["processName"].append(value)
        elif kind == "geoip":
            tag = f"geoip:{value}"
            if tag not in g["rule_set_build_in"]:
                g["rule_set_build_in"].append(tag)
        elif kind == "ip_cidr":
            if value not in g["ip_cidr"]:
                g["ip_cidr"].append(value)
        elif kind == "domain":
            if value not in g["domain"]:
                g["domain"].append(value)
        elif kind == "domain_suffix":
            if value not in g["domain_suffix"]:
                g["domain_suffix"].append(value)
        elif kind == "domain_keyword":
            if value not in g["domain_keyword"]:
                g["domain_keyword"].append(value)

    flush()
    return rules


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
        for key in (
            "rule_set_build_in",
            "rule_set",
            "processName",
            "ip_cidr",
            "domain",
            "domain_suffix",
            "domain_keyword",
        ):
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


def apply_local(rules: list[dict]) -> None:
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
    use_path.write_text(
        json.dumps(use, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

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
    entries = parse_surge_rules()
    print(f"surge.conf [Rule] entries: {len(entries)}")
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
                "source": "surge.conf",
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

    print("\n=== GROUPS (from surge.conf) ===")
    for r in rules:
        extras = []
        if r.get("processName"):
            extras.append(f"proc={len(r['processName'])}")
        if r.get("ip_cidr"):
            extras.append(f"cidr={len(r['ip_cidr'])}")
        print(
            f"  [{r['outbound']:16}] {r['name']}  "
            f"remote={len(r.get('rule_set', []))} "
            f"builtin={len(r.get('rule_set_build_in', []))} "
            f"{' '.join(extras)}"
        )
    rs_count = len(list(OUT_RS.glob("*.json")))
    print(f"\nwrote diversion_rules_custom.json ({len(rules)} groups)")
    print(f"ruleset json files: {rs_count}")
    if failed:
        print(f"FAILED downloads: {len(failed)}")
        for url, err in failed:
            print(f"  {url}: {err}")

    # Ensure AI process names are complete (Karing: exact match only)
    for r in rules:
        if r.get("name") == "🤖 AI" and "processName" in r:
            r["processName"] = list(AI_PROCESS_NAMES)
            break
    # rewrite diversion file with updated process names
    (OUT / "diversion_rules_custom.json").write_text(
        json.dumps({"rules": rules}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_runtime(rules)

    apply_local(rules)


if __name__ == "__main__":
    main()
