#!/usr/bin/env python3
"""Apply this repo's diversion rules into the *running Mac* Karing data dir.

Why this exists
---------------
Editing ``Group Containers/group.com.nebula.karing/*.json`` works until Karing
restarts: the app often rewrites ``karing_routing_group.json``,
``karing_subscribe_use.json`` and ``service_core.json`` from its own state and
drops groups we injected (e.g. 🔒 Proton).

This script re-injects from the repo after a wipe, or after you pull new rules.

Usage
-----
::

    # 1) Prefer: quit Karing fully (menu Quit), then:
    python3 karing/apply_to_local_karing.py

    # 2) Open Karing → reconnect / enable TUN
    # 3) Check 分流列表 for 🔒 Proton, 🤖 AI, 🗑 字节网站

If the UI still does not show new groups, import once in the app:
``karing/diversion_rules_custom.json`` (设置 → 分流 → 导入).
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KARING_DIR = Path(__file__).resolve().parent
KARING = Path.home() / "Library/Group Containers/group.com.nebula.karing"

REPO_ROUTING = KARING_DIR / "karing_routing_group.json"
REPO_DIV = KARING_DIR / "karing_subscribe_use.diversion.json"
PROTON_LIST = ROOT / "Proton.list"
FEISHU_LIST = ROOT / "FeishuLark.list"
AI_LIST = ROOT / "AI.list"

LARK_PROCS = [
    "Lark",
    "Lark Helper",
    "Lark Helper (GPU)",
    "Lark Helper (Plugin)",
    "Lark Helper (Renderer)",
    "Lark Helper (Network)",
    "LarkSuite",
    "Feishu",
    "Feishu Helper",
    "Feishu Helper (GPU)",
    "Feishu Helper (Plugin)",
    "Feishu Helper (Renderer)",
]

# Keet / Hyperswarm — exact macOS process names from `ps` / lsof COMMAND.
# Note: worker is lowercase "bare", not "Bare". NetworkService lives in "Keet Helper".
P2P_PROCS = [
    "Keet",
    "Keet Helper",
    "Keet Helper (Renderer)",
    "bare",
]
P2P_PATHS = [
    "/Applications/Keet.app/Contents/MacOS/Keet",
    "/Applications/Keet.app/Contents/Frameworks/Keet Helper.app/Contents/MacOS/Keet Helper",
    "/Applications/Keet.app/Contents/Frameworks/Keet Helper (Renderer).app/Contents/MacOS/Keet Helper (Renderer)",
    "/Applications/Keet.app/Contents/Resources/app/node_modules/bare-sidecar/prebuilds/darwin-arm64/bare",
    "/Applications/Keet.app/Contents/Resources/app/node_modules/bare-sidecar/prebuilds/darwin-x64/bare",
]


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def uniq(xs: list) -> list:
    seen: set = set()
    out: list = []
    for x in xs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def parse_list(path: Path) -> tuple[list[str], list[str], list[str]]:
    domain: list[str] = []
    suffix: list[str] = []
    keyword: list[str] = []
    if not path.exists():
        die(f"missing {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 2:
            continue
        typ, val = parts[0].upper(), parts[1]
        if typ == "DOMAIN":
            domain.append(val)
        elif typ == "DOMAIN-SUFFIX":
            suffix.append(val)
        elif typ == "DOMAIN-KEYWORD":
            keyword.append(val)
    return uniq(domain), uniq(suffix), uniq(keyword)


def backup(name: str, bak: Path, ts: str) -> None:
    src = KARING / name
    if src.exists():
        shutil.copy2(src, bak / f"{name}.before_apply_{ts}")


def rname(r: dict) -> str:
    return r.get("name") or ""


def apply() -> None:
    if not KARING.exists():
        die(f"Karing data dir not found: {KARING}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = KARING / "backup"
    bak.mkdir(exist_ok=True)
    for name in (
        "karing_routing_group.json",
        "karing_subscribe_use.json",
        "service_core.json",
    ):
        backup(name, bak, ts)

    pd, ps, pk = parse_list(PROTON_LIST)
    fd, fs, fk = parse_list(FEISHU_LIST)
    ad, ass, ak = parse_list(AI_LIST)
    proton_markers = set(pd + ps + pk)

    # ----- routing_group -----
    live_rg = json.loads((KARING / "karing_routing_group.json").read_text(encoding="utf-8"))
    repo_rg = json.loads(REPO_ROUTING.read_text(encoding="utf-8"))
    # Drop groups we pin ourselves so re-apply is idempotent.
    groups = [
        g
        for g in live_rg["items"][0]["groups"]
        if g.get("name") not in ("🔒 Proton", "p2p")
    ]

    repo_proton = next(
        (g for g in repo_rg["items"][0]["groups"] if g.get("name") == "🔒 Proton"),
        None,
    )
    if repo_proton is None:
        repo_proton = {
            "groupid": "custom",
            "name": "🔒 Proton",
            "type": "",
            "or": True,
            "rule_set": [
                "https://raw.githubusercontent.com/yywill/clash_rules/main/karing/ruleset/personal-Proton.json"
            ],
            "domain": list(pd),
            "domain_suffix": list(ps),
            "domain_keyword": list(pk),
        }
    else:
        repo_proton = json.loads(json.dumps(repo_proton))
        repo_proton["domain"] = uniq(list(repo_proton.get("domain") or []) + pd)
        repo_proton["domain_suffix"] = uniq(
            list(repo_proton.get("domain_suffix") or []) + ps
        )
        repo_proton["domain_keyword"] = uniq(
            list(repo_proton.get("domain_keyword") or []) + pk
        )

    # Local p2p group (process-name → direct). Prefer repo definition, force proc list.
    repo_p2p = next(
        (g for g in repo_rg["items"][0]["groups"] if g.get("name") == "p2p"),
        None,
    )
    p2p_paths = [p for p in P2P_PATHS if Path(p).exists()]
    p2p_group = {
        "groupid": "custom",
        "name": "p2p",
        "type": "",
        "or": True,
        "processName": list(P2P_PROCS),
        # Karing UI/macOS rewrite reads this field; keep exact process names.
        "process_name_macos": list(P2P_PROCS),
    }
    if p2p_paths:
        p2p_group["processPath"] = p2p_paths
        p2p_group["process_path_macos"] = p2p_paths
    if repo_p2p is not None:
        # Preserve any extra fields from repo, then force process matchers.
        merged = json.loads(json.dumps(repo_p2p))
        merged.update(p2p_group)
        p2p_group = merged

    for g in groups:
        name = g.get("name")
        if name == "🍃 Google":
            for key in ("domain", "domain_suffix", "domain_keyword"):
                vals = g.get(key) or []
                g[key] = [
                    x
                    for x in vals
                    if x not in proton_markers
                    and "proton" not in x.lower()
                    and x != "pm.me"
                ]
            g["rule_set"] = [
                u for u in (g.get("rule_set") or []) if "Proton" not in u
            ]
        elif name == "🗑 字节网站":
            g["domain"] = uniq(list(g.get("domain") or []) + fd)
            g["domain_suffix"] = uniq(list(g.get("domain_suffix") or []) + fs)
            g["domain_keyword"] = uniq(list(g.get("domain_keyword") or []) + fk)
            g["processName"] = uniq(list(g.get("processName") or []) + LARK_PROCS)
        elif name == "🤖 AI":
            g["domain"] = list(ad)
            g["domain_suffix"] = list(ass)
            g["domain_keyword"] = list(ak)

    # p2p first (highest priority among custom groups), Proton after Google.
    groups.insert(0, p2p_group)
    names = [g.get("name") for g in groups]
    idx = names.index("🍃 Google") + 1 if "🍃 Google" in names else len(groups)
    groups.insert(idx, repo_proton)
    for i, g in enumerate(groups):
        g["index"] = i
    live_rg["items"][0]["groups"] = groups
    (KARING / "karing_routing_group.json").write_text(
        json.dumps(live_rg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"✓ karing_routing_group.json — p2p @ index 0, 🔒 Proton @ index {idx}")

    # ----- diversion bindings -----
    use_path = KARING / "karing_subscribe_use.json"
    use = json.loads(use_path.read_text(encoding="utf-8"))
    repo_div = json.loads(REPO_DIV.read_text(encoding="utf-8"))
    live_by = {d.get("diversion_name"): d for d in (use.get("diversion_group") or [])}
    for d in repo_div.get("diversion_group") or []:
        live_by[d["diversion_name"]] = d
    order = [d["diversion_name"] for d in repo_div.get("diversion_group") or []]
    merged: list[dict] = []
    seen: set[str] = set()
    for n in order:
        if n in live_by:
            merged.append(live_by[n])
            seen.add(n)
    for n, d in live_by.items():
        if n not in seen:
            merged.append(d)
    # guarantee Proton binding
    if not any(d.get("diversion_name") == "🔒 Proton" for d in merged):
        merged.append(
            {
                "diversion_groupid": "custom",
                "diversion_name": "🔒 Proton",
                "server_groupid": "urltest",
                "server_name": "🇭🇰 香港节点",
                "dns_servers": [],
            }
        )
    # Guarantee p2p → direct at the front of diversion bindings.
    p2p_bind = {
        "diversion_groupid": "custom",
        "diversion_name": "p2p",
        "server_groupid": "direct",
        "server_name": "direct_out",
        "dns_servers": [],
    }
    merged = [d for d in merged if d.get("diversion_name") != "p2p"]
    merged.insert(0, p2p_bind)
    # Keep final last if present.
    finals = [d for d in merged if d.get("diversion_groupid") == "final"]
    non_final = [d for d in merged if d.get("diversion_groupid") != "final"]
    merged = non_final + finals

    use["diversion_group"] = merged
    use_path.write_text(
        json.dumps(use, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    proton_bind = next(d for d in merged if d.get("diversion_name") == "🔒 Proton")
    print(
        f"✓ karing_subscribe_use.json — p2p → direct; 🔒 Proton → "
        f"{proton_bind.get('server_name')} ({proton_bind.get('server_groupid')})"
    )

    # ----- service_core -----
    core_path = KARING / "service_core.json"
    core = json.loads(core_path.read_text(encoding="utf-8"))
    core.setdefault("route", {})["find_process"] = True
    rules = core["route"]["rules"]
    new_rules: list[dict] = []
    for r in rules:
        n = rname(r)
        if "Proton" in n:
            continue
        # Drop stale p2p rules (Karing may rewrite with wrong "Bare" casing).
        if n.startswith("p2p"):
            continue
        if "Google" in n:
            for b in r.get("rules") or [r]:
                for key in ("domain", "domain_suffix", "domain_keyword"):
                    if key in b:
                        b[key] = [
                            x
                            for x in b[key]
                            if x not in proton_markers
                            and "proton" not in x.lower()
                            and x != "pm.me"
                        ]
        new_rules.append(r)

    p2p_paths_exist = [p for p in P2P_PATHS if Path(p).exists()]
    p2p_process_rule: dict = {
        "outbound": "direct_out",
        "name": "p2p[进程]",
        "process_name": list(P2P_PROCS),
    }
    if p2p_paths_exist:
        p2p_process_rule["process_path"] = p2p_paths_exist
    p2p_custom_rule = {
        "rules": [
            {
                "process_name": list(P2P_PROCS),
                **({"process_path": p2p_paths_exist} if p2p_paths_exist else {}),
            }
        ],
        "outbound": "direct_out",
        "action": None,
        "name": "p2p[自定义]",
        "type": "logical",
        "mode": "or",
    }

    # Insert p2p at highest practical priority: right before first [自定义] rule
    # (after sniff / karing built-ins).
    insert_at = next(
        (i for i, r in enumerate(new_rules) if "[自定义]" in rname(r)),
        len(new_rules),
    )
    new_rules[insert_at:insert_at] = [p2p_process_rule, p2p_custom_rule]
    print(f"✓ service_core.json — p2p[进程]/p2p[自定义] → direct_out @{insert_at}")

    proton_rule = {
        "rules": [
            {
                "domain": list(pd),
                "domain_suffix": list(ps),
                "domain_keyword": list(pk),
            }
        ],
        "outbound": "urltest_out-🇭🇰 香港节点",
        "action": None,
        "name": "🔒 Proton[自定义]",
        "type": "logical",
        "mode": "or",
    }
    gidx = next((i for i, r in enumerate(new_rules) if "Google" in rname(r)), None)
    if gidx is None:
        new_rules.append(proton_rule)
    else:
        new_rules.insert(gidx + 1, proton_rule)

    if not any("Lark/Feishu" in rname(r) for r in new_rules):
        bidx = next((i for i, r in enumerate(new_rules) if "字节" in rname(r)), 11)
        new_rules.insert(
            bidx,
            {
                "rules": [{"process_name": list(LARK_PROCS)}],
                "outbound": "direct_out",
                "action": None,
                "name": "🗑 Lark/Feishu进程[自定义]",
                "type": "logical",
                "mode": "or",
            },
        )

    for r in new_rules:
        if "字节" not in rname(r):
            continue
        for b in r.get("rules") or [r]:
            b["domain"] = uniq(list(b.get("domain") or []) + fd)
            b["domain_suffix"] = uniq(list(b.get("domain_suffix") or []) + fs)
            b["domain_keyword"] = uniq(list(b.get("domain_keyword") or []) + fk)
            b["process_name"] = uniq(list(b.get("process_name") or []) + LARK_PROCS)

    # AI matchers (narrow, no broad googleapis.com)
    for r in new_rules:
        if "🤖 AI" not in rname(r):
            continue
        for b in r.get("rules") or [r]:
            b["domain"] = list(ad)
            b["domain_suffix"] = list(ass)
            b["domain_keyword"] = list(ak)

    # RFC1918 / link-local destinations must match before process→UDP (mosh/hy2),
    # otherwise local mosh is forced onto a remote UDP outbound and fails.
    priv_i = next(
        (
            i
            for i, r in enumerate(new_rules)
            if r.get("ip_is_private") or rname(r) == "ip_is_private"
        ),
        None,
    )
    if priv_i is not None:
        priv = new_rules.pop(priv_i)
        insert_priv = next(
            (
                i
                for i, r in enumerate(new_rules)
                if "process_name" in json.dumps(r) or "processName" in json.dumps(r)
            ),
            11,
        )
        new_rules.insert(insert_priv, priv)
        print(
            f"✓ service_core.json — ip_is_private → direct before process rules (@{insert_priv})"
        )

    core["route"]["rules"] = new_rules

    # Fix process names everywhere in core (route + dns). Karing sometimes
    # rewrites bare as "Bare", which never matches the real process.
    def _fix_process_names(obj: object) -> int:
        changed = 0
        if isinstance(obj, dict):
            for key, val in list(obj.items()):
                if key in ("process_name", "processName", "process_name_macos") and isinstance(
                    val, list
                ):
                    new: list[str] = []
                    for x in val:
                        if x == "Bare":
                            new.append("bare")
                            changed += 1
                        else:
                            new.append(x)
                    # If this looks like a Keet/p2p matcher, force the full set.
                    if any(x in new for x in ("Keet", "Keet Helper", "bare")):
                        for w in P2P_PROCS:
                            if w not in new:
                                new.append(w)
                                changed += 1
                    obj[key] = new
                else:
                    changed += _fix_process_names(val)
        elif isinstance(obj, list):
            for item in obj:
                changed += _fix_process_names(item)
        return changed

    fixed = _fix_process_names(core)
    if fixed:
        print(f"✓ service_core.json — fixed {fixed} process-name entries (Bare→bare / p2p set)")

    core_path.write_text(
        json.dumps(core, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("✓ service_core.json — 🔒 Proton[自定义] → 香港节点")

    # ----- verify -----
    rg = json.loads((KARING / "karing_routing_group.json").read_text(encoding="utf-8"))
    use2 = json.loads(use_path.read_text(encoding="utf-8"))
    core2 = json.loads(core_path.read_text(encoding="utf-8"))
    ok_p2p_r = any(g.get("name") == "p2p" for g in rg["items"][0]["groups"])
    ok_p2p_d = any(d.get("diversion_name") == "p2p" for d in use2.get("diversion_group") or [])
    ok_p2p_c = any(rname(r).startswith("p2p") for r in core2["route"]["rules"])
    p2p_g = next(g for g in rg["items"][0]["groups"] if g.get("name") == "p2p")
    ok_procs = set(p2p_g.get("processName") or []) >= set(P2P_PROCS)
    ok_r = any(g.get("name") == "🔒 Proton" for g in rg["items"][0]["groups"])
    ok_d = any(
        d.get("diversion_name") == "🔒 Proton"
        for d in use2.get("diversion_group") or []
    )
    ok_c = any("Proton" in rname(r) for r in core2["route"]["rules"])
    print()
    print("VERIFY")
    print(f"  routing_group has p2p: {ok_p2p_r} procs={p2p_g.get('processName')}")
    print(f"  diversion_group has p2p→direct: {ok_p2p_d}")
    print(f"  service_core has p2p rule: {ok_p2p_c}")
    print(f"  routing_group has 🔒 Proton: {ok_r}")
    print(f"  diversion_group has 🔒 Proton: {ok_d}")
    print(f"  service_core has Proton rule: {ok_c}")
    if not (ok_p2p_r and ok_p2p_d and ok_p2p_c and ok_procs and ok_r and ok_d and ok_c):
        die("apply incomplete")

    print()
    print("Next:")
    print("  1. Prefer: fully Quit Karing, then reopen → connect.")
    print("     (If Karing is open it may rewrite files on exit.)")
    print("  2. 分流列表 first custom group should be p2p (Keet/bare → 直连).")
    print("  3. If UI still empty after restart, run again:")
    print("       python3 karing/apply_to_local_karing.py")
    print("     or import in UI:")
    print(f"       {KARING_DIR / 'diversion_rules_custom.json'}")
    print(f"  Backup: {bak}/*before_apply_{ts}*")


if __name__ == "__main__":
    apply()
