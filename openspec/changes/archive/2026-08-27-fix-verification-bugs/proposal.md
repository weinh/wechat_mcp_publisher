## Why

2026-08-27 真机验证端到端打通（个人未认证订阅号实测可调素材/草稿接口），同时暴露两个实现 bug 与一批过时表述：① 微信返回 `text/plain` 无 charset 时中文 errmsg 被按 Latin-1 解码成乱码（`å°é¢è£åª...`）；② `examples/simple_usage.py` 内嵌 hex JPEG 损坏，冒烟脚本无法运行；③ README/服务器说明/错误提示中"未认证账号会 48001"的表述被实测推翻，且 newspic 小图报 53402 的经验未记录。

## What Changes

- **P0：`core/client.py::_request` 请求体改为字面 UTF-8**（`json.dumps(..., ensure_ascii=False)`）——微信草稿接口会把 `\uXXXX` 转义当字面文本入库，此前所有经 API 建的中文草稿标题/内容全是 `每日...` 乱码（真机回环已验证修复：中文入库回读正常）。`stable_token` 请求体同改保持一致
- `core/client.py::_json_of` 解析前强制 `response.encoding = "utf-8"`，杜绝响应侧中文乱码
- `core/client.py::list_drafts` 总数字段修正：微信实际返回 `total_count`（此前读 `total_item_count` 恒为 0）
- `core/exceptions.py` 错误表新增 `53402`（封面裁剪失败）提示：建议使用正常尺寸图片；`48001` 提示措辞纠偏
- `examples/simple_usage.py` 弃用坏 hex，改为程序生成 600×600 PNG（兼顾封面对裁剪尺寸的要求）
- README 与 `server/app.py` 服务器说明中的 48001 表述更新为实测结论（素材/草稿可用；`freepublish` 实测 48001 确为认证墙）

## Capabilities

### New Capabilities
（无）

### Modified Capabilities
- `mcp-server`: "工具错误可读且不泄露凭据"要求新增 errmsg 编码不乱码场景（微信 `text/plain` 响应下中文提示必须可读）

## Impact

- 代码：`core/client.py`（1 行）、`core/exceptions.py`（2 条文案）、`examples/simple_usage.py`、`server/app.py`（说明文本）
- 测试：responses 以 `text/plain` 返回 UTF-8 中文 errmsg 的复现用例；53402 提示断言
- 文档：README 已知限制段重写
- 无行为破坏；线上载荷不变
