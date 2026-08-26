"""core/client.py：token 生命周期与自愈重试（responses mock HTTP）。"""

from __future__ import annotations

import time

import pytest
import responses

from wechat_mcp_publisher.config import Config
from wechat_mcp_publisher.core.client import WeChatClient
from wechat_mcp_publisher.core.exceptions import WeChatAPIError

BASE = "https://api.weixin.qq.com"
TOKEN_URL = f"{BASE}/cgi-bin/stable_token"
DRAFT_LIST_URL = f"{BASE}/cgi-bin/draft/batchget"

CFG = Config(app_id="wx-appid", app_secret="wx-secret")


def make_client() -> WeChatClient:
    return WeChatClient(CFG)


def token_response(body=None):
    return responses.post(
        TOKEN_URL, json=body or {"access_token": "TOKEN-1", "expires_in": 7200}
    )


def draft_list_response(body=None):
    return responses.post(
        DRAFT_LIST_URL, json=body or {"total_item_count": 0, "item": [], "offset": 0}
    )


def _token_calls() -> int:
    return sum(1 for c in responses.calls if "stable_token" in c.request.url)


def _draft_calls() -> int:
    return sum(1 for c in responses.calls if "draft/batchget" in c.request.url)


@responses.activate
def test_token_fetched_once_and_reused_within_validity():
    token_response()
    draft_list_response()
    client = make_client()

    client.list_drafts()
    client.list_drafts()
    client.list_drafts()

    assert _token_calls() == 1, "有效期内多次调用不应重复获取 token"


@responses.activate
def test_token_refreshed_when_near_expiry():
    client = make_client()
    token_response()
    draft_list_response()

    client.list_drafts()  # 首次获取
    # 手动把过期时间拨到 5 分钟临界线以内
    client._token_expires_at = time.time() + 100
    token_response()
    client.list_drafts()

    assert _token_calls() == 2, "临近过期应自动刷新 token"


@responses.activate
def test_retry_once_on_expired_token_then_succeed():
    # 业务请求先 40001，刷新 token 后重试成功
    draft_list_response({"errcode": 40001, "errmsg": "invalid credential"})
    draft_list_response({"total_item_count": 0, "item": [], "offset": 0})
    token_response()
    token_response()
    client = make_client()

    page = client.list_drafts()

    assert page.total == 0
    assert _token_calls() == 2, "自愈应强制刷新一次 token"
    assert _draft_calls() == 2, "业务请求应恰好重试一次"


@responses.activate
def test_retry_only_once_then_raise():
    draft_list_response({"errcode": 40001, "errmsg": "invalid credential"})
    draft_list_response({"errcode": 40001, "errmsg": "invalid credential"})
    token_response()
    token_response()
    client = make_client()

    with pytest.raises(WeChatAPIError) as excinfo:
        client.list_drafts()

    assert excinfo.value.errcode == 40001
    assert _draft_calls() == 2, "重试一次失败后不得发起第三次请求"


@responses.activate
def test_error_code_raised_with_hint():
    draft_list_response({"errcode": 48001, "errmsg": "api unauthorized"})
    token_response()
    client = make_client()

    with pytest.raises(WeChatAPIError) as excinfo:
        client.list_drafts()

    assert "48001" in str(excinfo.value)
    assert "认证" in str(excinfo.value), "已知错误码应附带处置提示"


@responses.activate
def test_token_never_in_error_text():
    draft_list_response({"errcode": 40164, "errmsg": "invalid ip 1.2.3.4"})
    token_response()
    client = make_client()

    with pytest.raises(WeChatAPIError) as excinfo:
        client.list_drafts()

    assert "TOKEN-1" not in str(excinfo.value)
