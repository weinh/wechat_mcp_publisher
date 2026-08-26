## Context

仓库为空，从零建库。用户的公众号为**个人未认证订阅号**：`material/*`、`draft/*` 接口预计返回 `48001`（未授权），因此真机端到端验证要等认证账号到位，开发期以 mock 测试为主。内容转换（md→html）由用户已有的另一个 MCP 承担，本工具的入口是 HTML。使用形态：单用户、本地 stdio、单账号。

## Goals / Non-Goals

**Goals:**
- 本地 stdio MCP 服务器，暴露 5 个工具：`create_news_draft`、`create_newspic_draft`、`list_drafts`、`get_draft`、`delete_draft`
- token 生命周期完全内部化（获取、缓存、提前刷新、失效重试），LLM 不可见
- 图片处理内部化：封面上传、正文内嵌图上传与 URL 替换、newspic 多图上传
- 微信 errcode → 中文可读错误（含处置提示），token 永不出现在错误/日志中
- 核心逻辑（`core/`）可脱离 MCP 层独立 mock 测试

**Non-Goals:**
- markdown→HTML 转换（上游 MCP 负责）
- 发布（`freepublish`，认证后另立 change）
- 多账号；独立图片上传工具；HTML 微信子集校验/修复；素材清理工具

## Decisions

**D1：MCP 框架 = 官方 `mcp` SDK（2.x `MCPServer`），stdio 传输，同步工具函数**
实现时 `mcp` 已发布 2.x：原 `FastMCP` 改名为 `MCPServer`（`from mcp.server.mcpserver import MCPServer`），API 形状不变（`MCPServer(name=...)` / `@server.tool()` / `run(transport="stdio")`），实现按 2.x 适配，不回退锁版。备选：独立 FastMCP 2.x 项目（代理/中间件/auth 等能力，本项目用不上，多一个依赖和版本追逐）。同步函数在线程池中执行，本地单用户场景无并发压力，不需要 async。

**D2：HTTP = `requests`（同步）**
备选：`httpx`（async 原生）。D1 已定同步工具函数，requests 更简单。所有 HTTP 调用收敛在 `core/client.py`，将来要换 httpx 只动一处。

**D3：token = `POST /cgi-bin/stable_token`，进程内缓存，提前 5 分钟刷新**
备选：`GET /cgi-bin/token`——经典接口，但每次获取会使旧 token 在 5 分钟宽限后失效；本地工具进程频繁重启，stable_token 不会互相踩。缓存只在内存（单进程生命周期），不落盘。每日获取配额有限，缓存策略保证正常使用远碰不到配额。

**D4：图文/图片消息 = 两个独立工具，不用 `msg_type` 判别式单工具**
两者参数形状差异本质（HTML vs 纯文本、封面 vs 图列表），合并进一个 schema 需要条件必填，LLM 易传错组合。

**D5：HTML 内嵌图 = 正则扫描替换，不用 BeautifulSoup**
只改 `<img>` 的 `src` 值，其余 HTML 字节保持不变（bs4 序列化会重排版用户 HTML）。支持三种 src：本地路径、http(s) 外链（下载后上传）、data URI（解码后上传）；已经是微信域名（`mmbiz.qpic.cn`、`mp.weixin.qq.com`）的跳过。扫描与替换（纯文本处理）放 `utils/helpers.py`，上传调用走 `core/client.py`。

**D6：`content` 参数双形态 = 文件存在即路径，否则为内容字符串**
`os.path.exists(content)` 为真且可读 → 读文件；否则视为 HTML/文本本体。规则简单，写进工具 docstring。

**D7：错误处理 = `core/exceptions.py` 统一映射，工具抛出可读中文错误**
已知码给处置提示：`40164`（IP 不在白名单）→ 提示去后台加白名单；`48001`（接口未授权）→ 提示未认证账号限制；`40001/42001`（token 失效）→ 触发 D8；`40005/40007` 等 → 原样 errmsg + 参数建议。未知码原样透出 errcode/errmsg。

**D8：token 失效自愈 = 业务调用遇 `40001/42001` 时强制刷新一次并重试**
只重试一次，再失败即报错，避免死循环。

**D9：配置 = `.env`（`WECHAT_APP_ID` / `WECHAT_APP_SECRET`），python-dotenv 加载，启动时 fail-fast**
缺配置直接拒绝启动并给出设置指引，而不是等到第一次调用才炸。

**D10：测试 = pytest + `responses`（拦截 requests）**
`core/` 全部走 mock HTTP 测；工具层 monkeypatch core。真机冒烟脚本放 `examples/`，等认证账号后手动跑。

**D11：项目布局 = 与参考结构完全一致，仅去除两个文件**

参考结构逐项对齐（顶层文件、包内层级、tests/examples 均一致）。偏离仅两处：不设 `tools/access_token.py`（token 对 LLM 不可见是规格要求）、不设 `tools/publish.py`（发布属认证后的后续 change）。职责落位：微信全部 HTTP 接口（token、素材上传、草稿增删查）收敛于 `core/client.py`；图片下载/校验与 HTML 内嵌图替换等文件处理归 `utils/helpers.py`（参考结构注释即"日志、文件处理等辅助功能"）；草稿创建编排（content 双形态识别、图片编排、组装提交）在 `tools/draft.py`，查询/删除直接转发在 `tools/material.py`。

```
wechat-mcp-publisher/
├── pyproject.toml                 # uv 管理（D12）
├── README.md
├── .env.example
├── .gitignore
├── src/
│   └── wechat_mcp_publisher/
│       ├── __init__.py
│       ├── __main__.py            # stdio 启动入口：uv run python -m wechat_mcp_publisher
│       ├── config.py              # .env 加载与校验（D9）
│       ├── server/
│       │   ├── __init__.py
│       │   └── app.py             # FastMCP 实例 + 工具注册
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── draft.py           # create_news_draft / create_newspic_draft（含创建编排）
│       │   └── material.py        # list_drafts / get_draft / delete_draft
│       ├── core/
│       │   ├── __init__.py
│       │   ├── client.py          # 全部微信 HTTP 封装：stable_token / add_material / uploadimg / draft 增删查（含 token 生命周期 D3/D8）
│       │   ├── models.py          # 数据模型（dataclass / Pydantic）
│       │   └── exceptions.py      # errcode 映射（D7）
│       └── utils/
│           ├── __init__.py
│           └── helpers.py         # 日志、文件处理：图片下载/校验、HTML img src 替换
├── tests/
│   ├── __init__.py
│   ├── test_tools/                # 工具层测试（monkeypatch core）
│   └── test_core/                 # core 单测（responses mock HTTP）
└── examples/
    └── simple_usage.py            # 用法演示，兼真机冒烟（认证后验证 40164/48001）
```

**D12：包管理 = uv**
pyproject 由 uv 管理，依赖经 `uv add`（运行依赖 `mcp`、`requests`、`python-dotenv`；dev 依赖 `pytest`、`responses`），锁定在 `uv.lock`；Python 版本要求 ≥3.10（官方 `mcp` SDK 下限）。运行、测试、示例统一走 `uv run`；MCP 客户端的 stdio 接入命令为 `uv run python -m wechat_mcp_publisher`。备选：pip + venv / poetry——uv 单工具覆盖 venv、依赖、锁定与运行，本地开发链路最短。

## Risks / Trade-offs

- [未认证账号调 `draft/*` 全部 `48001`] → 开发期 mock 测试覆盖全部路径；错误映射含明确提示；`examples/simple_usage.py` 兼作认证后的真机验证入口
- [本地 IP 变动导致 `40164`] → 错误信息透出微信返回的当前 IP（errmsg 自带）+ 后台配置路径提示
- [正则替换漏掉非常规写法的 `<img>`] → v1 接受：漏掉的图保持原样（微信可能不显示），错误可见可改；不支持的情形在 docstring 说明
- [永久素材随上传堆积（删草稿不删素材）] → 已知负债，v1 不做清理工具，README 记录
- [上游 HTML 不符合微信子集导致排版异常] → 属上游 MCP 职责，本工具不校验不修复，README 说明边界
- [sync requests 在线程池执行] → 本地单用户可接受；若未来多并发再换 httpx（D2 已收敛改动面）

## Migration Plan

全新项目，无迁移。回滚 = 删除代码。真机验证顺序：配 `.env` → 配 IP 白名单 → 跑 `examples/simple_usage.py`（token → 上传 → 建草稿，逐步暴露 40164/48001）。

## Open Questions

- `48001` 假设未被实测（等有可用账号后用 smoke test 确认；不影响开发）
- newspic 字数上限以微信接口报错为准，工具侧先做宽松校验（非空、≤20 图）
