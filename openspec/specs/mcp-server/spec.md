# mcp-server Specification

## Purpose

以 stdio 传输运行微信公众号草稿发布 MCP 服务器：启动时从 `.env`/环境变量加载单账号凭据，注册 5 个草稿相关工具，并以可读、不泄露凭据的方式返回工具错误。

## Requirements

### Requirement: stdio MCP 服务器启动
系统 SHALL 以 stdio 传输运行 MCP 服务器（`python -m wechat_mcp_publisher`），并在启动时注册全部 5 个工具：`create_news_draft`、`create_newspic_draft`、`list_drafts`、`get_draft`、`delete_draft`。

#### Scenario: 正常启动
- **WHEN** 环境变量 `WECHAT_APP_ID` 与 `WECHAT_APP_SECRET` 均已配置，执行 `python -m wechat_mcp_publisher`
- **THEN** 服务器在 stdio 上就绪，MCP 客户端 `tools/list` 能看到且仅能看到上述 5 个工具及其参数 schema

#### Scenario: 缺少配置时拒绝启动
- **WHEN** `WECHAT_APP_ID` 或 `WECHAT_APP_SECRET` 未配置
- **THEN** 启动立即失败，错误信息说明缺哪个变量、`.env` 应放在哪里，不进入服务循环

### Requirement: 单账号配置加载
系统 SHALL 通过 `.env` 文件或进程环境变量读取唯一的账号凭据（`WECHAT_APP_ID`、`WECHAT_APP_SECRET`），MUST NOT 支持或要求在工具调用时传入凭据；同时 SHALL 解析可选行为开关 `WECHAT_NEED_OPEN_COMMENT` / `WECHAT_ONLY_FANS_CAN_COMMENT`（接受 1/0/true/false，不区分大小写；未设置视为未指定，非法值启动即报错并指明变量名与合法取值）与默认作者名 `WECHAT_AUTHOR`（任意字符串，首尾去空白，空白视为未设置）。

#### Scenario: .env 加载
- **WHEN** 工作目录存在含有效凭据的 `.env` 文件
- **THEN** 启动时凭据被加载并校验通过

#### Scenario: 行为开关非法值拒绝启动
- **WHEN** `WECHAT_NEED_OPEN_COMMENT` 或 `WECHAT_ONLY_FANS_CAN_COMMENT` 被设置为白名单外的值（如 `maybe`）
- **THEN** 启动失败，错误信息指明变量名与合法取值（1/0/true/false）

### Requirement: 工具错误可读且不泄露凭据
工具失败时 SHALL 返回包含错误原因与处置提示的中文错误信息；任何错误信息、日志或返回值中 MUST NOT 出现 access_token 或 AppSecret；微信接口返回的中文 errmsg（含 `text/plain` 无 charset 响应）SHALL 被正确按 UTF-8 解码，MUST NOT 出现编码乱码。

#### Scenario: 微信侧错误透传为可读信息
- **WHEN** 任一工具调用导致微信 API 返回错误码
- **THEN** 工具返回该错误码对应的中文说明及处置提示，且不含 token/secret

#### Scenario: text/plain 响应的中文 errmsg 不乱码
- **WHEN** 微信接口以 `Content-Type: text/plain`（无 charset）返回 UTF-8 编码的中文 errmsg（如 53402 封面裁剪失败）
- **THEN** 工具错误信息中的 errmsg 为可读中文，而非形如 `å°é¢è£åª` 的乱码

#### Scenario: 敏感值不泄露
- **WHEN** 工具因任何原因失败
- **THEN** 错误文本与日志中不包含 access_token 与 AppSecret 的值
