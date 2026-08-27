"""草稿创建工具：图文（news）与图片消息（newspic）。

本模块是纯函数（不依赖 MCP 框架），由 server/app.py 统一注册为 MCP 工具；
编排职责：content 双形态识别、内嵌图上传替换、封面/多图上传、组装提交。
"""

from __future__ import annotations

from typing import Any, Optional

from ..config import (
    DEFAULT_AUTHOR,
    DEFAULT_NEED_OPEN_COMMENT,
    DEFAULT_ONLY_FANS_CAN_COMMENT,
    resolve_setting,
)
from ..core.client import get_client
from ..utils.helpers import load_image, replace_inline_images, resolve_content

NEWSPIC_MIN_IMAGES = 1
NEWSPIC_MAX_IMAGES = 20

# 微信图文硬性上限（按字符计）：超限在本地预校验，避免上传图片后才失败
NEWS_TITLE_MAX_CHARS = 64
NEWS_DIGEST_MAX_CHARS = 120


def _validate_news_fields(title: str, digest: str) -> None:
    """本地预校验图文字段长度（微信上限：标题 64 字、摘要 120 字）。"""
    if len(title) > NEWS_TITLE_MAX_CHARS:
        raise ValueError(
            f"标题超长：当前 {len(title)} 字，微信上限 {NEWS_TITLE_MAX_CHARS} 字"
        )
    if len(digest) > NEWS_DIGEST_MAX_CHARS:
        raise ValueError(
            f"摘要超长：当前 {len(digest)} 字，微信上限 {NEWS_DIGEST_MAX_CHARS} 字"
            "（留空则微信自动截取正文）"
        )


def _resolve_comment_flags(
    client,
    need_open_comment: Optional[bool],
    only_fans_can_comment: Optional[bool],
) -> dict[str, int]:
    """三层解析留言开关（入参 > .env > 内置默认），输出微信要求的 0/1 整数。"""
    cfg = client.config
    return {
        "need_open_comment": int(
            resolve_setting(
                need_open_comment,
                cfg.need_open_comment,
                DEFAULT_NEED_OPEN_COMMENT,
            )
        ),
        "only_fans_can_comment": int(
            resolve_setting(
                only_fans_can_comment,
                cfg.only_fans_can_comment,
                DEFAULT_ONLY_FANS_CAN_COMMENT,
            )
        ),
    }


def create_news_draft(
    title: str,
    content: str,
    cover: str,
    author: Optional[str] = None,
    digest: str = "",
    content_source_url: str = "",
    need_open_comment: Optional[bool] = None,
    only_fans_can_comment: Optional[bool] = None,
) -> dict[str, Any]:
    """创建图文草稿（news），成功返回 {"media_id": ..., "title": ..., "cover_url": ...}。

    参数：
      title: 文章标题（必填，上限 64 字）
      content: 正文。支持两种形态——HTML 字符串，或本地 .html 文件路径
               （若该路径存在则自动读取文件，否则按 HTML 内容处理）
      cover: 封面图片（必填）：本地文件路径或 http(s) URL，自动上传为封面素材
      author: 作者名（可选，不传用 .env 或默认空；传空字符串可显式覆盖 .env）
      digest: 摘要（可选，上限 120 字，留空时微信自动截取正文）
      content_source_url: 原文链接（可选）
      need_open_comment: 是否开启留言（可选，不传用 .env 或默认开启）
      only_fans_can_comment: 是否仅粉丝可评论（可选，不传用 .env 或默认关闭）

    正文 HTML 中的 <img> 会自动上传到微信并替换 src 为微信托管的 URL；
    已指向微信域名（mmbiz.qpic.cn / mp.weixin.qq.com）的图片保持不变。
    """
    title = (title or "").strip()
    if not title:
        raise ValueError("title 不能为空")
    _validate_news_fields(title, digest or "")

    content_html = resolve_content(content or "")
    if not content_html.strip():
        raise ValueError("content 不能为空：请提供 HTML 内容或指向 .html 文件的路径")

    client = get_client()

    def _upload_inline(src: str) -> str:
        filename, data = load_image(src)  # 不存在/格式/大小问题在此报错，不建草稿
        return client.upload_inline_image(filename, data)

    processed_html = replace_inline_images(content_html, _upload_inline)

    cover_name, cover_data = load_image(cover)
    material = client.upload_permanent_image(cover_name, cover_data)

    article = {
        "title": title,
        "author": str(
            resolve_setting(author, client.config.author, DEFAULT_AUTHOR)
        ),
        "digest": digest,
        "content": processed_html,
        "content_source_url": content_source_url,
        "thumb_media_id": material.media_id,
        **_resolve_comment_flags(client, need_open_comment, only_fans_can_comment),
    }
    media_id = client.create_draft([article])
    return {"media_id": media_id, "title": title, "cover_url": material.url}


def create_newspic_draft(
    title: str,
    images: list[str],
    content: str = "",
    need_open_comment: Optional[bool] = None,
    only_fans_can_comment: Optional[bool] = None,
) -> dict[str, Any]:
    """创建图片消息草稿（newspic），成功返回 {"media_id": ..., "title": ..., "image_count": ...}。

    参数：
      title: 消息标题（必填）
      images: 1~20 张图片，按传入顺序展示；每项为本地文件路径或 http(s) URL
      content: 图片下方的纯文字说明（可选，注意不是 HTML）
      need_open_comment: 是否开启留言（可选，不传用 .env 或默认开启）
      only_fans_can_comment: 是否仅粉丝可评论（可选，不传用 .env 或默认关闭）

    与图文消息不同：图片消息的 content 是纯文本，图片本体在 images 中，
    全部经永久素材接口上传后按序组装。
    """
    title = (title or "").strip()
    if not title:
        raise ValueError("title 不能为空")

    if images is None or not isinstance(images, list):
        raise ValueError("images 必须是图片路径列表")
    if not (NEWSPIC_MIN_IMAGES <= len(images) <= NEWSPIC_MAX_IMAGES):
        raise ValueError(
            f"图片消息需要 {NEWSPIC_MIN_IMAGES}~{NEWSPIC_MAX_IMAGES} 张图片，当前 {len(images)} 张"
        )

    client = get_client()
    image_list: list[dict[str, str]] = []
    for source in images:
        filename, data = load_image(source)
        material = client.upload_permanent_image(filename, data)
        image_list.append({"image_media_id": material.media_id})

    article = {
        "article_type": "newspic",
        "title": title,
        "content": content or "",
        "image_info": {"image_list": image_list},
        **_resolve_comment_flags(client, need_open_comment, only_fans_can_comment),
    }
    media_id = client.create_draft([article])
    return {"media_id": media_id, "title": title, "image_count": len(image_list)}
