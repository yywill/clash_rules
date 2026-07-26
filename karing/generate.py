#!/usr/bin/env python3
"""Generate Karing diversion preset + sing-box rulesets from Clash .list files."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
OUT_RS = OUT / "ruleset"
BASE = "https://raw.githubusercontent.com/yywill/clash_rules/main/karing/ruleset"


def parse_clash_list(path: Path) -> dict[str, list[str]]:
    domain: list[str] = []
    domain_suffix: list[str] = []
    domain_keyword: list[str] = []
    ip_cidr: list[str] = []
    process_name: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
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
        elif typ == "PROCESS-NAME":
            if "*" in val or "/" in val or "%" in val:
                continue
            process_name.append(val)

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
        "process_name": uniq(process_name),
    }


def to_singbox_ruleset(parsed: dict[str, list[str]]) -> dict:
    rule = {
        k: parsed[k]
        for k in ("domain", "domain_suffix", "domain_keyword", "ip_cidr")
        if parsed[k]
    }
    return {"version": 2, "rules": [rule] if rule else []}


def rule(
    name: str,
    outbound: str,
    *,
    build_in: list[str] | None = None,
    rule_set: list[str] | None = None,
    domain_suffix: list[str] | None = None,
    domain_keyword: list[str] | None = None,
    domain: list[str] | None = None,
    ip_cidr: list[str] | None = None,
    process_name: list[str] | None = None,
    package: list[str] | None = None,
    enabled: bool = True,
) -> dict:
    r: dict = {"name": name, "outbound": outbound, "switch": enabled}
    if build_in:
        r["rule_set_build_in"] = build_in
    if rule_set:
        r["rule_set"] = rule_set
    if domain_suffix:
        r["domain_suffix"] = domain_suffix
    if domain_keyword:
        r["domain_keyword"] = domain_keyword
    if domain:
        r["domain"] = domain
    if ip_cidr:
        r["ip_cidr"] = ip_cidr
    if process_name:
        r["processName"] = process_name
    if package:
        r["package"] = package
    return r


def rs(name: str) -> str:
    return f"{BASE}/{name}.json"


def build_rules() -> list[dict]:
    return [
        rule("🗑 字节网站", "direct", build_in=["acl:ByteDance"]),
        rule("🟢 微信", "direct", build_in=["acl:Wechat"]),
        rule(
            "🎯 游戏下载直连",
            "direct",
            build_in=["acl:GameDownload", "acl:PublicDirectCDN"],
        ),
        rule(
            "🎮 游戏平台",
            "currentSelected",
            build_in=[
                "acl:Sony",
                "acl:Xbox",
                "acl:Epic",
                "acl:Origin",
                "acl:Steam",
                "acl:Nintendo",
                "acl:Blizzard",
            ],
        ),
        rule(
            "🤖 AI",
            "currentSelected",
            build_in=[
                "acl:AI",
                "acl:OpenAi",
                "acl:Claude",
                "acl:ClaudeAI",
                "acl:Gemini",
                "acl:Bing",
                "geosite:openai",
                "geoip:openai",
                "geosite:category-ai-!cn",
            ],
            rule_set=[rs("AI")],
            process_name=["ChatGPT", "Claude", "Cursor", "Antigravity"],
        ),
        rule("📲 nostr", "currentSelected", rule_set=[rs("nostr")]),
        rule(
            "🖥 Work",
            "currentSelected",
            rule_set=[rs("work")],
            domain_suffix=["slack.com", "googlevideo.com"],
        ),
        rule(
            "👨🏿‍💻 GitHub",
            "currentSelected",
            build_in=["acl:Github", "geosite:github", "geoip:github"],
            rule_set=[rs("GitHub")],
            process_name=["GitHub Desktop", "GitHub Desktop Helper"],
        ),
        rule(
            "🪙 Crypto",
            "currentSelected",
            build_in=[
                "acl:Crypto",
                "acl:Binance",
                "geosite:category-cryptocurrency",
            ],
        ),
        rule(
            "🎵 TikTok",
            "currentSelected",
            build_in=["geosite:tiktok", "acl:TikTok"],
        ),
        rule(
            "📹 YouTube",
            "currentSelected",
            build_in=["geosite:youtube", "acl:YouTube", "acl:YouTubeMusic"],
            package=["com.google.android.youtube"],
        ),
        rule(
            "🎥 Netflix",
            "currentSelected",
            build_in=[
                "geosite:netflix",
                "geoip:netflix",
                "acl:Netflix",
                "acl:NetflixIP",
            ],
        ),
        rule(
            "🍀 Google",
            "currentSelected",
            build_in=["acl:Google", "geosite:google", "geoip:google"],
        ),
        rule("🍎 AppleNews", "currentSelected", build_in=["acl:AppleNews"]),
        rule(
            "🎥 DiscoveryPlus",
            "currentSelected",
            build_in=["acl:DiscoveryPlus"],
        ),
        rule("🎥 DisneyPlus", "currentSelected", build_in=["acl:DisneyPlus"]),
        rule("🎥 MAX美国", "currentSelected", build_in=["acl:HBO"]),
        rule("🎥 HBO香港亚洲", "currentSelected", build_in=["acl:HBO_GO_HKG"]),
        rule("🎥 PBS", "currentSelected", build_in=["acl:PBS"]),
        rule("🎵 Spotify", "currentSelected", build_in=["acl:Spotify"]),
        rule(
            "👙 porn",
            "currentSelected",
            build_in=["acl:Porn", "acl:Pornhub"],
        ),
        rule("🌍 国外媒体", "currentSelected", build_in=["acl:ProxyMedia"]),
        rule("🎯 直连补充", "direct", rule_set=[rs("Direct")]),
        rule(
            "🎯 全球直连",
            "direct",
            build_in=[
                "acl:LocalAreaNetwork",
                "acl:UnBan",
                "acl:GoogleCN",
                "acl:SteamCN",
                "acl:ChinaDomain",
                "acl:ChinaCompanyIp",
                "acl:ChinaIp",
                "acl:Download",
                "acl:ChinaMedia",
                "geosite:cn",
                "geoip:cn",
            ],
        ),
        rule("📢 FCM", "currentSelected", build_in=["acl:GoogleFCM"]),
        rule(
            "🪟 Microsoft",
            "currentSelected",
            build_in=[
                "acl:Microsoft",
                "geosite:microsoft",
                "geosite:microsoft-dev",
                "geosite:microsoft-pki",
            ],
        ),
        rule(
            "🍎 Apple",
            "direct",
            build_in=[
                "acl:Apple",
                "geosite:apple",
                "geosite:apple-dev",
                "geosite:apple-pki",
                "geosite:apple-update",
            ],
        ),
        rule(
            "📲 Telegram",
            "currentSelected",
            build_in=["acl:Telegram", "geosite:telegram", "geoip:telegram"],
            package=["org.telegram.messenger", "org.telegram.messenger.web"],
            process_name=["Telegram", "Telegram.exe"],
        ),
        rule(
            "🚀 代理补充",
            "currentSelected",
            rule_set=[rs("ProxyLite")],
            build_in=["acl:ProxyLite"],
        ),
        rule(
            "🚀 节点选择",
            "currentSelected",
            build_in=["acl:ProxyGFWlist", "geosite:geolocation-!cn"],
        ),
        rule(
            "🛑 广告拦截",
            "block",
            build_in=["acl:BanAD", "geosite:category-ads"],
        ),
        rule(
            "🍃 应用净化",
            "block",
            build_in=["acl:BanProgramAD", "acl:BanADCompany"],
        ),
        rule(
            "📺 哔哩哔哩",
            "direct",
            build_in=["acl:Bilibili", "acl:BilibiliHMT"],
        ),
        rule("🎶 网易音乐", "direct", build_in=["acl:NetEaseMusic"]),
    ]


def main() -> None:
    OUT_RS.mkdir(parents=True, exist_ok=True)
    personal = {
        "AI": ROOT / "AI.list",
        "nostr": ROOT / "nostr.list",
        "work": ROOT / "work.list",
        "Direct": ROOT / "Direct.list",
        "ProxyLite": ROOT / "ProxyLite.list",
        "GitHub": ROOT / "GitHub.list",
    }
    for name, path in personal.items():
        parsed = parse_clash_list(path)
        rs_data = to_singbox_ruleset(parsed)
        (OUT_RS / f"{name}.json").write_text(
            json.dumps(rs_data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"wrote ruleset/{name}.json")

    rules = build_rules()
    (OUT / "diversion_rules_custom.json").write_text(
        json.dumps({"rules": rules}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote diversion_rules_custom.json ({len(rules)} groups)")

    groups = []
    diversion_use = []
    rule_set_items = []
    seen_urls: set[str] = set()
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
            "domain_suffix",
            "domain_keyword",
            "domain",
            "ip_cidr",
            "processName",
            "package",
        ):
            if key in r:
                g[key] = r[key]
        if "rule_set" in r:
            for url in r["rule_set"]:
                if url in seen_urls:
                    continue
                seen_urls.add(url)
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
        json.dumps(routing, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (OUT / "karing_subscribe_use.diversion.json").write_text(
        json.dumps({"diversion_group": diversion_use}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print("wrote karing_routing_group.json")
    print("wrote karing_subscribe_use.diversion.json")


if __name__ == "__main__":
    main()
