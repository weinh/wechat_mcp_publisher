## Why

草稿的留言设置（`need_open_comment` 开启留言 / `only_fans_can_comment` 仅粉丝可评论）当前在代码中硬编码为 0，用户无法控制；公众号希望默认开启留言（`need_open_comment=1`）、默认不限制仅粉丝（`only_fans_can_comment=0`），且能按文章灵活覆盖。

## What Changes

- 两个创建工具（`create_news_draft` / `create_newspic_draft`）新增可选参数 `need_open_comment` / `only_fans_can_comment`（bool，默认不传）
- 新增 `.env` 变量 `WECHAT_NEED_OPEN_COMMENT` / `WECHAT_ONLY_FANS_CAN_COMMENT`，用于改写默认值（接受 1/0/true/false）
- 三层解析优先级：**用户入参 > `.env` > 内置默认**（内置：`need_open_comment=True`、`only_fans_can_comment=False`）
- 提交给微信时仍转换为接口要求的 0/1 整数
- 行为变化：此前硬编码两项均为 0；此后未配置时 `need_open_comment` 默认变 1

## Capabilities

### New Capabilities
（无）

### Modified Capabilities
- `draft-management`: 创建类工具签名新增留言开关参数，新增"留言设置三层解析"要求（含优先级矩阵场景）
- `mcp-server`: 配置加载扩展为同时承载凭据与行为开关，新增对应要求

## Impact

- **代码**：`config.py`（新变量解析）、`tools/draft.py`（参数 + 解析 + 0/1 转换）、`core/client.py`（暴露 config）
- **配置**：`.env.example` 增加两个可选项说明
- **测试**：解析矩阵（入参赢 / .env 覆盖默认 / 内置兜底）、线上载荷为 0/1
- **兼容**：既有调用不传新参数时，`need_open_comment` 行为由 0 变 1（有意为之的默认值变更）
