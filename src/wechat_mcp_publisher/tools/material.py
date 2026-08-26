"""草稿查询与删除工具（list / get / delete），直接转发 core 客户端。"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ..core.client import get_client


def list_drafts(offset: int = 0, count: int = 20) -> dict[str, Any]:
    """分页查询草稿箱列表，返回 {"total": 总数, "offset": 当前偏移, "items": [{media_id, title, update_time}]}。

    参数：
      offset: 起始位置（默认 0）
      count: 每页数量（默认 20，最大 20）
    """
    page = get_client().list_drafts(offset=offset, count=count)
    return {
        "total": page.total,
        "offset": page.offset,
        "items": [asdict(item) for item in page.items],
    }


def get_draft(media_id: str) -> dict[str, Any]:
    """查询草稿详情（含 news_item 全部字段：标题、正文 HTML、封面等）。

    参数：
      media_id: 草稿 ID（由 create_news_draft / create_newspic_draft 返回，或从 list_drafts 获取）
    """
    media_id = (media_id or "").strip()
    if not media_id:
        raise ValueError("media_id 不能为空")
    return get_client().get_draft(media_id)


def delete_draft(media_id: str) -> dict[str, Any]:
    """删除指定草稿，成功返回 {"media_id": ..., "deleted": true}。

    注意：删除草稿不会连带删除其占用的永久素材图片（微信行为）。
    参数：
      media_id: 草稿 ID
    """
    media_id = (media_id or "").strip()
    if not media_id:
        raise ValueError("media_id 不能为空")
    get_client().delete_draft(media_id)
    return {"media_id": media_id, "deleted": True}
