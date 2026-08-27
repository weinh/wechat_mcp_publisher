## Context

v1 中 `need_open_comment` / `only_fans_can_comment` 在 `tools/draft.py` 组装 article 时硬编码为 0。本次引入三层可配置，且不改变微信接口形态（线上仍是 0/1 整数）。

## Goals / Non-Goals

**Goals:**
- 两个创建工具暴露留言开关（对 LLM 友好的 bool 类型）
- 默认值可被 `.env` 改写，单次调用可被入参覆盖
- 优先级：入参 > `.env` > 内置默认（need_open_comment=True，only_fans_can_comment=False）

**Non-Goals:**
- 不改查询/删除工具；不改 token/图片链路；不引入其他草稿字段配置化

## Decisions

**D1：解析函数放 `config.py`，Config 增加两个可选布尔字段（None = 未设置）**
`load_config()` 解析 `WECHAT_NEED_OPEN_COMMENT` / `WECHAT_ONLY_FANS_CAN_COMMENT`，接受 `1/0/true/false/yes/no`（不区分大小写），非法值报 `ConfigError` 指明变量名与合法取值；未设置则为 None。备选：在 tools 里各自解析——重复且测试面碎。

**D2：工具参数用 `bool | None = None`，提交前转 0/1**
MCP schema 对 LLM 而言 bool 比 0/1 更不易传错；`None` 表示"未指定，走配置链"。组装 article 时 `int(value)` 转换。备选：直接用 int 参数——LLM 传 0/1/2 等错值概率更高。

**D3：工具通过 `get_client().config` 取配置，避免二次 `load_config()`**
`WeChatClient` 增加只读属性 `config`，客户端单例即配置单例，两个创建工具共用。备选：工具里再调 `load_config()`——每次调用重复解析，且未来多配置源时两处维护。

**D4：解析顺序实现为一处通用纯函数 `resolve_setting(param, env_value, builtin)`**
三行纯函数放 `config.py`，bool/str 通用，两个工具三个字段共用，杜绝四处复制优先级逻辑。作者名用 `Optional[str]`：`None` 走配置链，空字符串是显式入参（可压过 `.env` 清空默认值）；`WECHAT_AUTHOR` 值首尾去空白、空白视为未设置。作者仅 news 生效——微信 newspic 草稿结构无作者字段。

## Risks / Trade-offs

- [默认行为变化：`need_open_comment` 由 0 变 1] → proposal 已声明为有意变更；README 与 .env.example 明示，想恢复旧行为设 `WECHAT_NEED_OPEN_COMMENT=0`
- [`.env` 值形态多样导致误配] → 白名单解析 + 非法值 fail-fast 报错（含变量名与合法值）
- [工具签名变长] → 两个新参数均可选且有中文 docstring 说明，对 LLM 无心智负担

## Migration Plan

无需迁移：旧调用（不传新参、不配新变量）自动落到新默认值。回滚 = 还原代码。

## Open Questions

（无——优先级语义已与用户确认：入参 > .env > 内置默认）
