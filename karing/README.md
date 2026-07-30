# Karing 分流配置

以本仓库 **`surge.conf` `[Rule]`** 为准：顺序、策略名、RULE-SET 全部同步；转换为 sing-box JSON 后由 Karing HTTPS 拉取。

## 文件

| 文件 | 用途 |
|------|------|
| `diversion_rules_custom.json` | 导入到 Karing 的整套自定义分流 |
| `ruleset/*.json` | Surge 里每条 RULE-SET 对应的规则集 |
| `generate.py` | 从 `surge.conf` 重新生成 |
| `ruleset_sources.json` | URL → 文件名映射 |

## 重新生成

```bash
python3 karing/generate.py
```

## 导入（换设备）

1. push 到 GitHub  
2. Karing → 设置 → 分流 → 分流规则 → 编辑 → ⋯ → **导入** → `diversion_rules_custom.json`  
3. 添加订阅时关闭「启用 ISP 分流规则」

## 说明

- 优先级与 Surge 一致（字节/微信置顶 → 游戏 CDN/平台 → AI → … → GFW/国内兜底 → 广告）
- `PROCESS-NAME`（如 Keet/bare、`mosh-client`）写入 Karing 进程规则
- 进程分流（不写 IP）：`mosh-client`/`mosh-server` → `💼 工作` → `🌐 全球 UDP 优选`；`ssh` → `🔐 SSH` → `🌐 全球 VLESS 稳定 TCP`
- `GEOIP,CN` / `IP-CIDR6` 写入对应分流组
- 默认动作对齐 Surge 策略组的**第一项**（如苹果/微软默认直连，广告拦截）
- Apple News 仅代理明确的新闻域名；iCloud、Apple Account、APNs、系统更新与
  升级包 CDN 均由 `AppleDirect.list` 提前直连，避免大流量更新误走代理
- 本地应用时开启 DNS 按分流规则解析，确保苹果直连域名不借道代理 DNS

## 自定义自动选择（地区与协议）

| 组 | 说明 |
|----|------|
| 🇭🇰 香港节点 | |
| 🇯🇵 日本节点 | |
| 🇺🇲 美国节点 | AI / OpenAi / Copilot / 🐳 OrbStack 默认；Apple News / 部分流媒体 |
| 🌏 东南亚节点 | 含新加坡；GitHub / TikTok 默认 |
| 🇨🇳 台湾节点 | |
| 🇰🇷 韩国节点 | |
| 🇪🇺 欧洲节点 | |
| 🇷🇺 俄罗斯节点 | |
| 🇮🇳 印度节点 | |
| 🕌 中东节点 | |
| 🌎 南美节点 | |
| 🌏 大洋洲节点 | |
| 🌐 全球 UDP 优选 | Hysteria2 / TUIC；游戏平台 / Mosh 默认 |
| 🌐 全球 VLESS 稳定 TCP | 原生 VLESS TCP（排除 WS / gRPC）；SSH / 通用流量默认 |

分流会直接绑定到对应的自动组（例如 AI → 美国），而不是绑定到
`currentSelected`。组内节点由 Karing 按延迟自动选择。

Karing/sing-box 的 `urltest` 是最低延迟自动选择，不是真正的轮询或连接级
负载均衡。`全球 UDP 优选` 直接按订阅节点的协议字段筛选 `hysteria2` 和
`tuic`（同时保留名称匹配作为兼容），不依赖节点名称必须带 `hy2`。
`全球 VLESS 稳定 TCP` 按协议字段筛选 `vless`，并只保留未设置额外传输层
（或显式为 TCP）的节点，避免把 VLESS over WebSocket / gRPC 混入稳定 TCP 组。
同时根据当前机场的 TCP 节点命名规律保留动态正则，新订阅刷新后符合相同命名
约定的节点可由 Karing 自动加入；协议与传输字段仍用于脚本重新生成时的精确校验。
GitHub、Nostr、Crypto、Telegram、porn 与未显式绑定的代理规则默认使用此组；
游戏平台仍使用 UDP 优选，AI 与流媒体继续使用对应地区组。

`🚀 节点选择`、`🐟 漏网之鱼`和最终兜底绑定 Karing 的“当前选择”
（`currentSelected`）。可在首页手工选择具体服务器，也可选择任一自动组。
