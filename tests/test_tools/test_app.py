"""server/app.py：注册面与错误可见性。"""

from __future__ import annotations

import asyncio

from wechat_mcp_publisher.core.exceptions import WeChatAPIError
from wechat_mcp_publisher.server.app import create_server

EXPECTED_TOOLS = {
    "create_news_draft",
    "create_newspic_draft",
    "list_drafts",
    "get_draft",
    "delete_draft",
}


def _tool_names() -> list[str]:
    result = asyncio.run(create_server().list_tools())
    tools = result.tools if hasattr(result, "tools") else result  # mcp 2.x 返回 list
    return [t.name for t in tools]


def test_exactly_five_tools_registered():
    names = _tool_names()
    assert set(names) == EXPECTED_TOOLS
    assert len(names) == 5


def test_no_token_tool_exposed():
    names = _tool_names()
    assert not any("token" in name.lower() for name in names), "token 管理不得注册为工具"


def test_tool_descriptions_present():
    result = asyncio.run(create_server().list_tools())
    tools = result.tools if hasattr(result, "tools") else result  # mcp 2.x 返回 list
    for tool in tools:
        assert tool.description, f"工具 {tool.name} 缺少 description（docstring）"


def test_known_error_hints_are_readable():
    error = WeChatAPIError(48001, "api unauthorized")
    text = str(error)
    assert "48001" in text and "认证" in text

    ip_error = WeChatAPIError(40164, "invalid ip 1.2.3.4 ipv6 ::ffff:1.2.3.4")
    assert "白名单" in str(ip_error)


def test_error_text_has_no_credential_values():
    error = WeChatAPIError(40013, "invalid appid")
    assert "wx-secret" not in str(error)
