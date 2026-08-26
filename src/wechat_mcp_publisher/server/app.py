"""MCP 服务器创建与工具注册入口（官方 mcp SDK 2.x：MCPServer）。"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from ..tools import draft as draft_tools
from ..tools import material as material_tools

_INSTRUCTIONS = """微信公众号草稿发布工具（本地 stdio）。

能力：创建图文/图片消息草稿、查询与删除草稿。
- 图文（news）正文吃 HTML：markdown→HTML 请先由其他工具完成
- 图片消息（newspic）的 content 是纯文本说明，图片在 images 参数里
- 正文内嵌图片会自动上传到微信并替换链接，无需手动处理
- access_token 由内部管理，无需也无法手动获取

当前账号若为个人未认证订阅号，素材/草稿接口会返回 48001（需认证账号）。"""

# 注册顺序即 tools/list 顺序
_TOOLS = (
    draft_tools.create_news_draft,
    draft_tools.create_newspic_draft,
    material_tools.list_drafts,
    material_tools.get_draft,
    material_tools.delete_draft,
)


def create_server() -> MCPServer:
    """创建 MCPServer 实例并注册全部工具。"""
    server = MCPServer(
        name="wechat-mcp-publisher",
        title="微信公众号草稿发布",
        instructions=_INSTRUCTIONS,
    )
    for tool_fn in _TOOLS:
        server.tool()(tool_fn)
    return server


# 模块级实例：__main__.py 与测试直接引用
server = create_server()
