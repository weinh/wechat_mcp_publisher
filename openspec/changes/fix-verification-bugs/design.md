## Context

真机验证发现：微信部分接口（素材/草稿）返回 `Content-Type: text/plain` 且不带 charset。requests 对 text/* 默认 ISO-8859-1 解码 → `r.json()` 得到乱码 errmsg。同次验证证实账号权限假设过时。

## Goals / Non-Goals

**Goals:** errmsg 中文可读；冒烟脚本可跑；文档与实测一致。

**Non-Goals:** 不做编码协商/自动探测（微信 API 恒为 UTF-8，固定即可）；不改任何接口行为。

## Decisions

**D1：`_json_of` 解析前 `response.encoding = "utf-8"`**
微信全部接口响应恒为 UTF-8，无需协商；一行修在唯一解析漏斗里。备选 `json.loads(response.content)`——绕过 requests 的 text 层，但改动面大一行不如一行。

**D2：`53402` 提示为"换正常尺寸图片"而非"检查裁剪参数"**
实测语境：newspic 首图充当封面需可裁剪，1×1 测试图必挂、600×600 即过——用户可执行的处置就是换图。

**D3：冒烟图改程序生成 600×600 PNG（zlib+struct，无新依赖）**
手写 hex 已翻车一次；PNG 结构简单可确定性生成，600×600 同时满足封面裁剪的最小可用尺寸经验。

**D4：48001 表述统一为"实测可用 + 提示保留但纠偏"**
错误表里 48001 的提示仍保留（部分接口/账号类型确实受限），但删去被推翻的"个人未认证订阅号不支持"断言；README 已知限制段改写为实测事实与 53402 经验。

## Risks / Trade-offs

- [固定 UTF-8 若遇非 UTF-8 响应] → 微信 API 无此形态，风险可忽略
- [600×600 仍可能不满足某些封面比例] → 53402 报错带明确提示，可迭代

## Migration Plan

纯修复，无迁移。

## Open Questions

（无）
