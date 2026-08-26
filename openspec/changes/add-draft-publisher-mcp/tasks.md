## 1. 项目脚手架

- [x] 1.1 用 uv 初始化项目：`uv init` 生成 pyproject（src-layout，requires-python ≥3.10），`uv add mcp requests python-dotenv`、`uv add --dev pytest responses`；建包骨架：`src/wechat_mcp_publisher/`（server/tools/core/utils 各含 `__init__.py`）、`tests/`（含 `__init__.py`、`test_core/`、`test_tools/`）、`examples/`
- [x] 1.2 创建 `.env.example`（`WECHAT_APP_ID` / `WECHAT_APP_SECRET`）、`.gitignore`（含 `.env`）、README 骨架（项目定位与 v1 边界）

## 2. 配置与错误基础

- [x] 2.1 实现 `config.py`：`.env` + 环境变量加载单账号凭据，缺失时 fail-fast 并输出设置指引
- [x] 2.2 实现 `core/exceptions.py`：`WeChatAPIError` 与 errcode → 中文提示映射（至少 40164、48001、40001/42001、40005、40007，未知码透传），错误文本不含 token/AppSecret

## 3. 核心客户端与 token 生命周期

- [x] 3.1 实现 `core/client.py`：requests 调用收敛、`stable_token` 获取、进程内缓存、剩余有效期 <5 分钟自动刷新
- [x] 3.2 实现业务请求遇 `40001/42001` 时强制刷新 token 并重试恰好一次的逻辑
- [x] 3.3 单测（responses mock）：有效期内复用 token、临近过期刷新、失效自愈成功、重试仍失败报错且无第二次重试

## 4. 图片处理

- [x] 4.1 实现 `core/client.py` 的图片接口封装（`add_material` 永久素材、`uploadimg` 正文内嵌）与 `utils/helpers.py` 文件处理辅助：本地路径 / http(s) URL 下载、存在性 / 格式 / 10MB 大小校验
- [x] 4.2 实现 `utils/helpers.py` 的正文 HTML 内嵌图扫描替换：本地/外链/data URI 经 `uploadimg` 上传换微信 URL，微信域名（`mmbiz.qpic.cn`、`mp.weixin.qq.com`）跳过，除 `src` 外 HTML 不改写
- [x] 4.3 单测（`tests/test_core/`，responses mock）：各 src 形态的替换与跳过、HTML 其余部分字节不变、超大/不支持格式报错、文件不存在不发起上传

## 5. 草稿核心

- [x] 5.1 定义 `core/models.py` 数据模型（草稿参数、微信响应的 dataclass/Pydantic 模型）；在 `core/client.py` 封装草稿接口：`draft/add`、`draft/batchget` 分页、`draft/get`、`draft/delete`
- [x] 5.2 实现 `tools/draft.py` 创建编排：news（content 双形态识别、内嵌图替换、封面上传、组装提交）、newspic（1~20 张校验、按序上传组装 `image_list`、任一失败不建草稿）；实现 `tools/material.py` 的 list/get/delete 转发
- [x] 5.3 单测（`tests/test_tools/` + `tests/test_core/`）：news 最小参数成功、`content` 为文件路径形态、newspic 数量越界报错、多图保序、中途上传失败不调用 `draft/add`、缺必填参数不发起微信请求

## 6. MCP 服务器与工具层

- [x] 6.1 实现 `server/app.py`：FastMCP 实例，挂载 `tools/draft.py`（`create_news_draft` / `create_newspic_draft`）与 `tools/material.py`（`list_drafts` / `get_draft` / `delete_draft`）注册的工具，docstring 说明 `content` 双形态识别规则
- [x] 6.2 实现 `__main__.py`：stdio 启动入口，启动时执行配置校验，缺失配置拒绝启动
- [x] 6.3 工具层测试（monkeypatch core）：`tools/list` 恰好 5 个工具且无 token 相关工具、参数 schema 正确、错误信息为可读中文且不含敏感值

## 7. 示例与文档收尾

- [x] 7.1 编写 `examples/simple_usage.py`：工具用法演示，兼作真机冒烟（token → 图片上传 → 建最小草稿），供认证账号到位后逐步验证 40164/48001
- [x] 7.2 编写 MCP 客户端接入示例（Claude Code / Claude Desktop 的 stdio 配置，command 为 `uv run python -m wechat_mcp_publisher`）与 `examples/simple_usage.py`
- [x] 7.3 完成 README：uv 安装与同步（`uv sync`）、配置、IP 白名单指引、已知限制（未认证 48001、删草稿不删素材的堆积负债、HTML 微信兼容性属上游职责）
