# Karing 分流配置

从本仓库 `clash.ini` **完整同步**规则集：下载/转换每一条 `.list` 为 sing-box JSON，Karing 用 HTTPS 拉取；顺序与 Clash/Surge 一致。

## 文件

| 文件 | 用途 |
|------|------|
| `diversion_rules_custom.json` | 导入到 Karing 的整套自定义分流 |
| `ruleset/*.json` | 全部规则集（个人 + ACL4SSR fork + ios_rule_script 等） |
| `generate.py` | 从 `clash.ini` 重新生成 |
| `ruleset_sources.json` | URL → 文件名映射（调试用） |

## 重新生成

```bash
python3 karing/generate.py
```

会：

1. 解析 `clash.ini` 全部 `ruleset=`
2. 下载各 `.list`（个人列表优先读本地文件）并转成 `ruleset/*.json`
3. 写出 `diversion_rules_custom.json`
4. 若本机有 Karing，写入本地分流配置（并内联规则，push 前也能用）

## 导入（换设备）

1. push 到 GitHub
2. Karing → 设置 → 分流 → 分流规则 → 编辑 → ⋯ → **导入** → 选 `diversion_rules_custom.json`
3. 添加订阅时关闭「启用 ISP 分流规则」

## 订阅

在 Karing 里直接加多个机场订阅即可，不必 Sub Store。
