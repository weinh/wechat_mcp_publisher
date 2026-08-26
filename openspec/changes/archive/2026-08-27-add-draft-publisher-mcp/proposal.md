## Why

用户希望让 LLM（MCP 客户端）直接把成稿内容搬进微信公众号草稿箱，替代"手动打开网页后台→粘贴→传图→排版"的重复操作。当前仓库为空，需从零建立一个本地 MCP 工具；账号现状为个人未认证订阅号，终局是认证后全自动发布，v1 先覆盖到"建草稿"为止。

## What Changes

- 新建 Python 项目 `wechat-mcp-publisher`：基于官方 `mcp` SDK 的 FastMCP、以 stdio 传输运行的本地 MCP 服务器
- 提供 5 个 MCP 工具：
  - `create_news_draft`（图文草稿：HTML 字符串或 `.html` 文件路径进，内部完成内嵌图上传换微信 URL、封面传素材）
  - `create_newspic_draft`（图片消息草稿：纯文本说明 + 1~20 张本地图片路径）
  - `list_drafts` / `get_draft` / `delete_draft`（草稿查询与清理）
- 内部机制（不暴露给 LLM）：access_token 获取与过期缓存、两套图片上传接口的区分调用、微信 errcode → 可读错误信息转换
- 配置：单账号，AppID/AppSecret 走 `.env`
- 明确不做（v1 范围外）：markdown→HTML 转换（用户已有独立 MCP 承担）、发布 `freepublish`（等账号认证后另立 change）、多账号、独立图片上传工具

## Capabilities

### New Capabilities
- `mcp-server`: stdio MCP 服务器生命周期、`.env` 单账号配置加载、工具注册面（5 个工具的对外契约）
- `access-token-management`: access_token 获取、过期缓存与自动刷新、对 LLM 完全隐藏
- `image-material-processing`: 图片素材上传（封面/图片消息走永久素材接口，正文内嵌图走 uploadimg 接口）与 HTML `<img>` 扫描替换
- `draft-management`: 图文（news）与图片消息（newspic）两种草稿的创建、查询、删除

### Modified Capabilities
（无——全新项目，无既有规格）

## Impact

- **代码**：全新代码库 `src/wechat_mcp_publisher/`（server / tools / core / utils 分层），`tests/`、`examples/`、`pyproject.toml`
- **依赖**：`mcp`（官方 SDK，含 FastMCP）、`requests`、`python-dotenv`；测试用 `pytest`
- **外部系统**：微信公众号 API——`stable_token`（或 `token`）、`material/add_material`、`media/uploadimg`、`draft/add`、`draft/batchget`、`draft/get`、`draft/delete`
- **已知风险（不阻塞开发，阻塞真机验证）**：
  - 个人未认证订阅号调用 `draft/*`、`material/*` 预计返回 `48001`，真机端到端验证需等认证账号到位（开发期以 mock 测试为主）
  - 获取 token 需在公众号后台配置 IP 白名单（本地工具 IP 会变，`40164` 需给出可操作的错误提示）
  - 输入 HTML 的微信兼容性（内联样式子集）由上游 md→html MCP 负责，本项目不做校验/修复
