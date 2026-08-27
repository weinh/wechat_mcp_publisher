# wechat-mcp-publisher

微信公众号草稿发布本地 MCP 工具。把「写好的 HTML → 公众号草稿箱」变成一次 LLM 工具调用：图片上传、正文内嵌图换微信 URL、封面素材、建草稿全部自动完成。

基于官方 `mcp` SDK（2.x `MCPServer`），stdio 传输，单账号，`uv` 管理依赖。

## 工具面（5 个）

| 工具 | 用途 |
|---|---|
| `create_news_draft` | 图文草稿：吃 HTML（或 `.html` 文件路径）+ 封面图 + 必填摘要；标题 ≤64 字、摘要 ≤120 字；内嵌 `<img>` 自动上传换微信 URL |
| `create_newspic_draft` | 图片消息草稿：必填文字说明（≤1000 字，HTML 标记自动清洗为纯文本）+ 1~20 张图（按序）；标题 ≤20 字 |
| `list_drafts` | 分页查草稿箱 |
| `get_draft` | 草稿详情（含正文） |
| `delete_draft` | 删除草稿（不连带删素材） |

`access_token` 由内部获取、缓存、失效自愈（`stable_token` + 40001/42001 自动刷新重试一次），**不暴露为工具**。错误统一转为带处置提示的中文信息（如 40164 提示加 IP 白名单、53402 提示换正常尺寸图片），且不含凭据。

## 默认值三层覆盖（留言开关 / 作者）

两个创建工具都支持 `need_open_comment`（开启留言）、`only_fans_can_comment`（仅粉丝可评论），图文工具另支持 `author`（作者名），按同一三层优先级解析：

```
工具入参 > .env 变量 > 内置默认
```

内置默认：开启留言、不限制仅粉丝、作者留空。想改写默认值，在 `.env` 里配置：

```bash
WECHAT_NEED_OPEN_COMMENT=0      # 整个账号默认关闭留言，个别文章仍可传参开启
WECHAT_AUTHOR=公众号编辑         # 图文默认作者名（图片消息无作者字段）
```

留言开关接受 1/0/true/false；作者名传空字符串入参可显式清空 `.env` 配置的默认值。

## 安装

```bash
uv sync
cp .env.example .env   # 填入 WECHAT_APP_ID / WECHAT_APP_SECRET
```

凭据获取：[mp.weixin.qq.com](https://mp.weixin.qq.com) → 设置与开发 → 基本配置。**同一页面需把本机公网 IP 加入 IP 白名单**，否则 token 获取报 `40164`。

已发布 PyPI 后也可免克隆直接运行（在含 `.env` 的目录）：

```bash
uvx wechat-mcp-publisher
# 或 pip install wechat-mcp-publisher && wechat-mcp-publisher
```

此时 MCP 客户端配置可简化为 `"command": "uvx", "args": ["wechat-mcp-publisher"]`。

## 接入 MCP 客户端

Claude Code（推荐，一条命令）：

```bash
claude mcp add wechat-mcp-publisher -- uv run --directory /你的路径/wechat-mcp-publisher python -m wechat_mcp_publisher
```

项目级配置（本仓库已内置 [.mcp.json](.mcp.json)，Claude Code 在本仓库目录打开即生效，首次需在 `/mcp` 中确认信任）：无需手动添加。

Claude Desktop / 其他客户端：把 [examples/mcp-client-config.example.json](examples/mcp-client-config.example.json) 中的片段合入对应配置文件。

## 使用示例

对 LLM 说：

> 帮我把 /path/article.html 发成公众号图文草稿，封面用 /path/cover.jpg

或图片消息：

> 把这三张图 /a.jpg /b.jpg /c.jpg 发成图片消息草稿，说明文字：周末出片

真实 API 链路演示见 [examples/simple_usage.py](examples/simple_usage.py)（token → 上传 → 建草稿，兼作真机冒烟）。

## 测试

```bash
uv run pytest
```

全部接口经 `responses` mock，不需要真实账号即可跑通。

## 范围与已知限制

- **不做 markdown→HTML 转换**：正文入口是 HTML，转换请用你已有的 md→html 工具完成
- **不做发布**（`freepublish`）：当前只到草稿；发布留给账号认证后扩展
- **账号权限**：个人未认证订阅号实测（2026-08）可正常调用素材/草稿接口、端到端建草稿；个别受限接口仍可能返回 `48001`（错误提示会说明）
- **封面裁剪**：图片消息（newspic）首图兼作封面，图片过小或比例异常会报 `53402`（1×1 实测失败、600×600 实测通过），请用正常尺寸图片
- **HTML 微信兼容性**：微信编辑器只认内联样式的 HTML 子集，排版适配由上游转换工具负责，本工具不校验不修复
- **素材堆积**：删除草稿不会删除其占用的永久素材图片，长期使用需偶尔在公众号后台清理
- 单账号：凭据来自 `.env`，不提供多账号切换
