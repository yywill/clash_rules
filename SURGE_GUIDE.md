# Surge Configuration Guide

## Overview

This repository manages proxy rules for **Surge** (iOS/macOS) and **Clash** (via Subconverter). All node subscriptions are managed through **Sub-Store** (`collection2`).

## Repository Layout

```
clash_rules/
├── surge.conf          # Native Surge config (used directly)
├── clash.ini           # Subconverter custom config (for Clash clients)
├── AI.list             # Custom: OpenAI, Claude, Gemini, Copilot, Perplexity, Cursor, etc.
├── nostr.list          # Custom: Nostr relays & clients (Damus, Primal, etc.)
├── work.list           # Custom: Work essentials (Google Meet, Slack)
├── Direct.list         # Custom: China direct-connect supplement
├── ProxyLite.list      # Custom: Proxy supplement (foreign DNS, specific IPs)
├── News.sgmodule       # Surge module: iRingo Apple News unlock (US)
└── LICENSE.md
```

## Forked Upstream Repos

| Repo | Purpose | Customizations |
|------|---------|----------------|
| `yywill/ACL4SSR` | ACL4SSR rule sets | ByteDance, Wechat, Crypto, Apple, HBO, Porn, etc. |
| `yywill/ios_rule_script` | blackmatrix7 rules | YouTube, Google, Telegram, GitHub, Speedtest |

Forking allows pulling upstream updates while keeping personal customizations.

## Proxy Group Hierarchy

### Selection Flow

```
┌─────────────────────────────────────────────────┐
│  🚀 Node Select (master selector)               │
│  🚀 Manual Switch (all raw nodes)               │
│  ♻️ Auto Select (url-test, best latency)         │
├─────────────────────────────────────────────────┤
│  Regional Groups (url-test per region)           │
│  ├── 🇭🇰 HK    🇨🇳 TW    🇸🇬 SG                  │
│  ├── 🇯🇵 JP    🇺🇲 US    🇰🇷 KR                  │
│  ├── 🛰 Satellite (Hysteria2 nodes)              │
│  └── 🎥 Netflix Nodes                            │
├─────────────────────────────────────────────────┤
│  Load Balance Groups                             │
│  ├── 🌍 Streaming LB - HK / US                  │
│  ├── 🌍 Developed Countries LB                   │
│  ├── 📲 Telegram LB                              │
│  ├── 📲 Nostr LB                                 │
│  └── 🎵 TikTok LB                               │
└─────────────────────────────────────────────────┘
```

### Clash.ini Additional Strategies

- **Fallback (故转)**: HK, JP, SG, US — auto-failover on node failure
- **Star Fallback (⭐)**: Cross-subscription fallback (`GROUPID=!0`)
- **Budget Fallback (🕊️)**: Low-cost nodes (JMS, 0.5x multiplier)
- **Full Load Balance**: Global LB, Non-HK LB, HK High-Speed LB

## Rule Ordering (Order Matters!)

Rules are evaluated top-to-bottom. First match wins.

### Priority 1: Force Direct / China-First Services
```
ByteDance (字节) → 🗑 字节网站 (Direct or HK)
WeChat (微信)    → 🟢 微信 (Direct or HK)
```
**Why first?** WeChat Pay and similar services break on non-HK proxies. Even HK routes are slow — Direct is preferred.

### Priority 2: AI Services
```
OpenAI        → 💬 OpenAi (prefers Satellite/Hysteria2)
Copilot/Bing  → 💧 Copilot (prefers Satellite)
AI.list       → 🤖 AI (Satellite → JP → US → SG)
Nostr         → 🤖 Nostr (Nostr LB)
```

### Priority 3: Crypto
```
Crypto exchanges → 🪙 Crypto (HK → SG → TW)
```

### Priority 4: Streaming (specific before general)
```
TikTok        → 🎵 TikTok (TikTok LB, non-HK)
YouTube       → 📹 油管视频 (Streaming LB-HK)
Netflix       → 🎥 奈飞视频 (HK or Netflix nodes)
Google        → 🍃 Google (HK LB or US LB)
Apple News    → 🍎 AppleNews (US nodes — requires US IP)
HBO Max       → 🎥 MAX美国 (US LB)
HBO Asia      → 🎥 HBO香港亚洲 (HK LB)
Spotify       → 🎵 Spotify (HK LB)
Foreign Media → 🌍 国外媒体 (US LB, catch-all)
```

### Priority 5: Direct Connect
```
UnBan, ChinaCompanyIp, Download → 🎯 全球直连
LocalAreaNetwork                → 🎯 全球直连
```

### Priority 6: Service-Specific (switchable)
```
Google FCM, Microsoft, Apple, Gaming → Default Direct, switchable
Telegram (duplicate rule)            → 📲 电报消息
NetEase Music                        → 🎶 网易音乐
```

### Priority 7: GFW & Ad Blocking
```
ProxyGFWlist   → 🚀 节点选择
ChinaDomain    → 🎯 全球直连
BanProgramAD   → 🍃 应用净化 (REJECT)
BanAD          → 🛑 广告拦截 (REJECT)
```

### Priority 8: Final / Catch-All
```
GEOIP CN               → 🎯 全球直连
IPv6 China ranges       → 🎯 全球直连
IPv6 all (::/0)         → 🐟 漏网之鱼
FINAL                   → 🐟 漏网之鱼
```

## General Settings

| Setting | Value | Rationale |
|---------|-------|-----------|
| IPv6 | `true` | Future-proofing ("时代进步了") |
| DNS | AliDNS + Tencent DNSPod + IPv6 | Domestic DNS for China resolution |
| DNS Hijack | 8.8.8.8, 8.8.4.4 | Intercept Google DNS to prevent leaks |
| GeoIP DB | Hackl0us GeoIP2-CN | More accurate China IP detection |
| Test Timeout | 2s | Aggressive — fast failover |
| Proxy Test URL | google.com/generate_204 | Standard liveness check |
| Internet Test | baidu.com | China-accessible connectivity check |
| Rule Update | 86400s (24h) | All rule sets refresh daily |
| Always Real IP | Gaming (Nintendo, PlayStation, Xbox, Battle.net) | Prevents gaming connectivity issues |

## Key Design Principles

1. **China-first services go Direct first** — WeChat, ByteDance must not accidentally proxy
2. **AI gets premium routing** — Satellite/Hysteria2 nodes preferred for low-latency AI access
3. **Specific before general** — YouTube before Foreign Media, Netflix before Foreign Media
4. **Load balancing for high-throughput** — Telegram, TikTok, streaming use LB groups
5. **Region-aware routing** — US for Apple News/HBO, HK for YouTube/Netflix, JP/SG for AI
6. **Forked upstreams** — Maintain control over rule sets while tracking community updates
7. **Dual format** — surge.conf for Surge, clash.ini for Subconverter/Clash

## How to Modify

### Adding a new service rule
1. Create or find the appropriate `.list` file
2. Add a `RULE-SET` entry in `surge.conf` at the correct priority position
3. Add corresponding `ruleset=` in `clash.ini`
4. Create a proxy group if the service needs dedicated routing

### Adding a new node region
1. Add a new `url-test` group with regex matching node names
2. Reference it in the master `🚀 节点选择` group
3. Optionally add to relevant LB groups

### Updating upstream rules
```bash
# In forked repos (ACL4SSR, ios_rule_script):
git fetch upstream
git merge upstream/master
# Push to yywill/ fork — surge.conf references raw.githubusercontent.com/yywill/...
```
