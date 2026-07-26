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
- `PROCESS-NAME`（如 Keet/bare）写入 Karing 进程规则
- `GEOIP,CN` / `IP-CIDR6` 写入对应分流组
- 默认动作对齐 Surge 策略组的**第一项**（如苹果/微软默认直连，广告拦截）

## 自定义自动选择（按国家）

只保留 4 组（无卫星）：🇭🇰 香港 / 🇯🇵 日本 / 🇸🇬 狮城 / 🇺🇲 美国。  
分流动作 = Surge 策略组里**第一个可用选项**（跳过已删除的卫星、以及「节点选择/手动切换/自动选择」元组）。

查看/改：设置 → 分流 → **自定义自动选择**。
