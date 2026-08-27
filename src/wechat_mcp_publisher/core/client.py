"""微信 API 客户端：所有 HTTP 交互的收敛点（D2/D3/D8）。

职责：
- stable_token 获取与进程内缓存（剩余有效期 <5 分钟自动刷新）
- 业务请求遇 40001/42001 时强制刷新 token 并重试恰好一次
- 永久素材上传（add_material）、正文内嵌图上传（uploadimg）
- 草稿增删查（draft/add、batchget、get、delete）
"""

from __future__ import annotations

import time
from typing import Any, Mapping

import requests

from ..config import Config
from ..utils.helpers import get_logger
from .exceptions import (
    TOKEN_EXPIRED_CODES,
    WeChatAPIError,
    WeChatResponseError,
    raise_for_code,
)
from .models import DraftPage, DraftSummary, MaterialImage

BASE_URL = "https://api.weixin.qq.com"

# token 剩余有效期低于该秒数时提前刷新（规格：5 分钟）
_TOKEN_REFRESH_MARGIN = 300.0

_TIMEOUT = 30.0
_UPLOAD_TIMEOUT = 60.0


class WeChatClient:
    """单账号微信 API 客户端。token 管理对调用方完全透明。"""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self._log = get_logger()

    @property
    def config(self) -> Config:
        """只读配置（工具层用于行为开关解析，凭据仍在内部管理）。"""
        return self._config

    # ------------------------------------------------------------------
    # token 生命周期（不对外暴露）
    # ------------------------------------------------------------------

    def _fetch_token(self, force: bool = False) -> str:
        if force:
            self._log.debug("强制刷新 access_token")
        response = requests.post(
            f"{BASE_URL}/cgi-bin/stable_token",
            json={
                "grant_type": "client_credential",
                "appid": self._config.app_id,
                "secret": self._config.app_secret,
            },
            timeout=_TIMEOUT,
        )
        payload = _json_of(response)
        token = payload.get("access_token")
        if not token:
            raise_for_code(payload)  # 失败形态形如 {"errcode":40013,...}
            raise WeChatAPIError(-1, "stable_token 未返回 access_token")
        self._token = str(token)
        expires_in = float(payload.get("expires_in", 7200))
        self._token_expires_at = time.time() + expires_in
        self._log.debug("access_token 已更新，有效期 %ss", int(expires_in))
        return self._token

    def _ensure_token(self) -> str:
        if (
            self._token is None
            or time.time() > self._token_expires_at - _TOKEN_REFRESH_MARGIN
        ):
            return self._fetch_token()
        return self._token

    def invalidate_token(self) -> None:
        """丢弃缓存 token（自愈重试前调用）。"""
        self._token = None
        self._token_expires_at = 0.0

    # ------------------------------------------------------------------
    # 请求漏斗：所有业务接口都经过这里
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        params: Mapping[str, Any] | None = None,
        *,
        json_body: Mapping[str, Any] | None = None,
        files: Mapping[str, Any] | None = None,
        timeout: float = _TIMEOUT,
        _retried: bool = False,
    ) -> dict[str, Any]:
        params = dict(params or {})
        params["access_token"] = self._ensure_token()
        response = requests.request(
            method,
            f"{BASE_URL}{path}",
            params=params,
            json=json_body,
            files=files,
            timeout=timeout,
        )
        payload = _json_of(response)
        errcode = int(payload.get("errcode", 0) or 0)
        if errcode in TOKEN_EXPIRED_CODES and not _retried:
            # token 失效自愈：强制刷新后重试恰好一次（D8）
            self.invalidate_token()
            return self._request(
                method,
                path,
                params,
                json_body=json_body,
                files=files,
                timeout=timeout,
                _retried=True,
            )
        raise_for_code(payload)
        return payload

    # ------------------------------------------------------------------
    # 图片接口
    # ------------------------------------------------------------------

    def upload_permanent_image(self, filename: str, data: bytes) -> MaterialImage:
        """上传永久素材图片：用于图文封面、图片消息（newspic）本体。"""
        payload = self._request(
            "POST",
            "/cgi-bin/material/add_material",
            params={"type": "image"},
            files=_image_file_field(filename, data),
            timeout=_UPLOAD_TIMEOUT,
        )
        return MaterialImage(
            media_id=str(payload["media_id"]), url=str(payload.get("url", ""))
        )

    def upload_inline_image(self, filename: str, data: bytes) -> str:
        """上传正文内嵌图片：返回微信托管的 URL（无 media_id）。"""
        payload = self._request(
            "POST",
            "/cgi-bin/media/uploadimg",
            files=_image_file_field(filename, data),
            timeout=_UPLOAD_TIMEOUT,
        )
        return str(payload["url"])

    # ------------------------------------------------------------------
    # 草稿接口
    # ------------------------------------------------------------------

    def create_draft(self, articles: list[dict[str, Any]]) -> str:
        """新建草稿，articles 结构由调用方（tools/draft.py）组装。"""
        payload = self._request(
            "POST", "/cgi-bin/draft/add", json_body={"articles": articles}
        )
        return str(payload["media_id"])

    def list_drafts(self, offset: int = 0, count: int = 20, *, no_content: bool = True) -> DraftPage:
        """分页查询草稿列表。no_content=True 时不返回正文，响应更轻。"""
        payload = self._request(
            "POST",
            "/cgi-bin/draft/batchget",
            json_body={
                "offset": offset,
                "count": count,
                "no_content": 1 if no_content else 0,
            },
        )
        items = [
            DraftSummary(
                media_id=str(item.get("media_id", "")),
                title=_first_title(item),
                update_time=int(item.get("update_time", 0) or 0),
            )
            for item in payload.get("item", [])
        ]
        return DraftPage(
            total=int(payload.get("total_item_count", 0) or 0),
            offset=int(payload.get("offset", offset) or offset),
            items=items,
        )

    def get_draft(self, media_id: str) -> dict[str, Any]:
        """查询草稿详情，返回微信原始结构（含 news_item 列表）。"""
        payload = self._request(
            "POST", "/cgi-bin/draft/get", json_body={"media_id": media_id}
        )
        return dict(payload)

    def delete_draft(self, media_id: str) -> bool:
        """删除草稿。注意：不连带删除其引用的永久素材（微信行为）。"""
        self._request("POST", "/cgi-bin/draft/delete", json_body={"media_id": media_id})
        return True


# ----------------------------------------------------------------------
# 模块级单例：工具层通过 get_client() 取用，测试可替换
# ----------------------------------------------------------------------

_client: WeChatClient | None = None


def get_client() -> WeChatClient:
    global _client
    if _client is None:
        # 延迟导入避免与 config 的循环依赖；凭据缺失在此处 fail-fast
        from ..config import load_config

        _client = WeChatClient(load_config())
    return _client


def reset_client() -> None:
    """清空单例（测试用）。"""
    global _client
    _client = None


# ----------------------------------------------------------------------
# 内部辅助
# ----------------------------------------------------------------------

_MIME_BY_EXT = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "bmp": "image/bmp",
}


def _image_file_field(filename: str, data: bytes) -> dict[str, Any]:
    import mimetypes

    mime = (
        mimetypes.guess_type(filename)[0]
        or _MIME_BY_EXT.get(filename.rsplit(".", 1)[-1].lower(), "image/jpeg")
    )
    return {"media": (filename, data, mime)}


def _json_of(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise WeChatResponseError(
            f"HTTP {response.status_code} {response.text!r}"
        ) from exc
    if not isinstance(payload, dict):
        raise WeChatResponseError(f"非对象响应：{payload!r}")
    return payload


def _first_title(item: Mapping[str, Any]) -> str:
    content = item.get("content") or {}
    news_item = content.get("news_item") or []
    if news_item and isinstance(news_item[0], dict):
        return str(news_item[0].get("title", ""))
    return ""
