"""数据模型：微信接口请求/响应的 dataclass（参考结构 core/models.py）。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MaterialImage:
    """永久素材图片上传结果（material/add_material）。"""

    media_id: str
    url: str = ""


@dataclass(frozen=True)
class DraftSummary:
    """草稿列表项（draft/batchget）。"""

    media_id: str
    title: str
    update_time: int = 0


@dataclass(frozen=True)
class DraftPage:
    """草稿列表分页结果。"""

    total: int
    offset: int
    items: list[DraftSummary] = field(default_factory=list)
