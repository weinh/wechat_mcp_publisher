"""辅助功能：日志、文件处理（图片下载/校验、HTML 内嵌图 src 替换）。

参考结构注释：日志、限流、文件处理等辅助功能。本项目的限流诉求由
core/client 的 token 缓存承担，这里聚焦文件与文本处理（D5）。
"""

from __future__ import annotations

import base64
import logging
import mimetypes
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

# 微信自有图片域名：src 指向它们时跳过，不重复上传
WECHAT_IMAGE_HOSTS = ("mmbiz.qpic.cn", "mp.weixin.qq.com")

# 微信图片接口支持的格式与大小上限（add_material / uploadimg 同限）
SUPPORTED_IMAGE_EXTS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".bmp"})
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB

_DOWNLOAD_TIMEOUT = 30.0

# 匹配 <img ... src="..."> 的 src 值：单双引号均可，捕获组 3 为 src 本体
_IMG_SRC_RE = re.compile(r'(<img\b[^>]*?\bsrc\s*=\s*)(["\'])(.*?)\2', re.IGNORECASE | re.DOTALL)

_DATA_URI_RE = re.compile(r"^data:image/(png|jpeg|jpg|gif|bmp);base64,(.*)$", re.IGNORECASE | re.DOTALL)


def get_logger(name: str = "wechat_mcp_publisher") -> logging.Logger:
    """统一命名空间的 logger（stderr 输出，绝不写 stdout 以免污染 stdio 协议）。"""
    return logging.getLogger(name)


# ----------------------------------------------------------------------
# content 双形态（D6）
# ----------------------------------------------------------------------


def resolve_content(content: str) -> str:
    """content 为已存在的文件路径时读取文件内容，否则原样返回。"""
    if content and os.path.isfile(content):
        get_logger().debug("content 为文件路径，读取：%s", content)
        return Path(content).read_text(encoding="utf-8")
    return content


# ----------------------------------------------------------------------
# 图片加载与校验
# ----------------------------------------------------------------------


def load_image(source: str) -> tuple[str, bytes]:
    """把图片来源统一为 (filename, data)。

    支持三种来源：本地路径、http(s) URL、data URI。
    文件不存在 / 下载失败 / 格式不支持 / 超过 10MB 时抛 ValueError 或 FileNotFoundError。
    """
    source = source.strip()
    if not source:
        raise ValueError("图片来源为空")

    if source.startswith("data:"):
        filename, data = _parse_data_uri(source)
    elif source.startswith(("http://", "https://")):
        filename, data = _download_image(source)
    else:
        filename, data = _read_local_image(source)

    validate_image(filename, data)
    return filename, data


def validate_image(filename: str, data: bytes) -> None:
    """上传前校验：微信支持的格式 + 不超过 10MB。不满足抛 ValueError。"""
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_IMAGE_EXTS:
        raise ValueError(
            f"不支持的图片格式「{filename}」：请使用 {'/'.join(sorted(SUPPORTED_IMAGE_EXTS))}"
        )
    if len(data) > MAX_IMAGE_SIZE:
        raise ValueError(
            f"图片「{filename}」大小 {len(data) / 1024 / 1024:.1f}MB，超过微信接口 10MB 限制"
        )
    if not data:
        raise ValueError(f"图片「{filename}」内容为空")


def is_wechat_image_url(url: str) -> bool:
    """src 是否已指向微信图片域名（无需再上传替换）。"""
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return False
    return host.lower() in WECHAT_IMAGE_HOSTS


# ----------------------------------------------------------------------
# HTML 内嵌图替换（D5）
# ----------------------------------------------------------------------


def replace_inline_images(html: str, uploader) -> str:
    """扫描 HTML 中全部 <img> 的 src，交由 uploader 上传并替换为微信 URL。

    - uploader(src) -> 新 URL；由调用方负责上传实现
    - src 已指向微信域名：跳过，不改写
    - 除 src 值外，HTML 其余部分保持逐字节不变
    """
    def _sub(match: re.Match[str]) -> str:
        prefix, quote, src = match.group(1), match.group(2), match.group(3)
        if not src:
            return match.group(0)
        if src.startswith(("http://", "https://")) and is_wechat_image_url(src):
            get_logger().debug("内嵌图已是微信域名，跳过：%s", src)
            return match.group(0)
        new_url = uploader(src)
        return f"{prefix}{quote}{new_url}{quote}"

    return _IMG_SRC_RE.sub(_sub, html)


# ----------------------------------------------------------------------
# 内部辅助
# ----------------------------------------------------------------------


def _read_local_image(path: str) -> tuple[str, bytes]:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"图片文件不存在：{path}")
    return os.path.basename(path), Path(path).read_bytes()


def _download_image(url: str) -> tuple[str, bytes]:
    try:
        response = requests.get(url, timeout=_DOWNLOAD_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ValueError(f"下载图片失败（{url}）：{exc}") from exc
    name = os.path.basename(unquote(urlparse(url).path)) or "image.jpg"
    return name, response.content


def _parse_data_uri(uri: str) -> tuple[str, bytes]:
    match = _DATA_URI_RE.match(uri.strip())
    if not match:
        raise ValueError("无法解析的 data URI，仅支持 base64 编码的图片")
    subtype, b64 = match.group(1).lower(), match.group(2)
    ext = {"jpeg": "jpg", "jpg": "jpg", "png": "png", "gif": "gif", "bmp": "bmp"}[subtype]
    try:
        data = base64.b64decode(b64)
    except (ValueError, base64.binascii.Error) as exc:  # type: ignore[attr-defined]
        raise ValueError(f"data URI base64 解码失败：{exc}") from exc
    return f"inline-image.{ext}", data


def guess_image_mime(filename: str) -> str:
    return mimetypes.guess_type(filename)[0] or "image/jpeg"
