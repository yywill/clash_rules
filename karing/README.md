# Karing 分流配置

对应本仓库的 Surge / Clash 策略：规则写在这里，Karing 通过 HTTPS 拉取个人规则集；常见服务走 Karing 内置 ACL / geosite。

## 文件

| 文件 | 用途 |
|------|------|
| `diversion_rules_custom.json` | 导入到 Karing 的自定义分流组（整套策略） |
| `ruleset/*.json` | 个人规则的 sing-box source 规则集（网络下载） |
| `karing_routing_group.json` | 运行时分流结构参考（一般不用手改） |

个人规则集 URL（push 到 `main` 后可用）：

```text
https://raw.githubusercontent.com/yywill/clash_rules/main/karing/ruleset/AI.json
https://raw.githubusercontent.com/yywill/clash_rules/main/karing/ruleset/nostr.json
https://raw.githubusercontent.com/yywill/clash_rules/main/karing/ruleset/work.json
https://raw.githubusercontent.com/yywill/clash_rules/main/karing/ruleset/Direct.json
https://raw.githubusercontent.com/yywill/clash_rules/main/karing/ruleset/ProxyLite.json
https://raw.githubusercontent.com/yywill/clash_rules/main/karing/ruleset/GitHub.json
```

## 导入步骤

1. 把本仓库改动 push 到 GitHub（规则集 URL 才能下载）
2. Karing → **设置** → **分流** → **分流规则** → **编辑**（自定义分流组）
3. 右上角 **⋯** → **导入** → 选择 `karing/diversion_rules_custom.json`
4. 确认各分流组动作（直连 / 当前选择 / 拦截），保存后回首页重连
5. 添加多个机场订阅即可（不必 Sub Store）；添加时**关闭「启用 ISP 分流规则」**

## 订阅

直接在 Karing 里加多条订阅链接。若仍想用 Sub Store 聚合：

```text
https://<你的-Sub-Store主机>/download/collection/collection2?target=Clash
```

不要用 Surge 模块劫持的 `https://sub.store/...`（Karing 不会走 Surge 模块）。

## 优先级（上 → 下，先匹配先生效）

字节/微信直连 → 游戏下载直连 → 游戏平台代理 → AI / nostr / Work / GitHub → 流媒体与 Crypto → 国内直连 → Telegram / Microsoft / Apple → GFW 兜底 → 广告拦截

与 `surge.conf` / `clash.ini` 对齐；节点策略组（负载均衡、故转）用 Karing 的「当前选择 / 自动选择 / 自定义代理组」在 App 里配。

## 更新个人规则

改根目录的 `AI.list` / `nostr.list` 等后，重新生成 ruleset 再 push：

```bash
python3 karing/generate.py
```
