"""真机冒烟 / 用法演示：token → 图片上传 → 建最小草稿。

用途：
- 平时：直接阅读本文件了解工具链怎么串
- 真机验证：`uv run python examples/simple_usage.py` 逐步验证链路

预期失败点（按顺序暴露）：
  40164  调用方 IP 不在白名单 → 去公众号后台加白名单后重跑
  40013/40125  AppID/AppSecret 有误 → 检查 .env
  53402  封面裁剪失败 → 测试图太小（脚本已用 600×600，正常不会遇到）
"""

from __future__ import annotations

import struct
import sys
import tempfile
import zlib
from pathlib import Path


def _smoke_png(width: int = 600, height: int = 600) -> bytes:
    """生成纯色 PNG 冒烟图（不依赖外部素材；尺寸满足封面裁剪要求）。"""
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return (
            struct.pack(">I", len(data))
            + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8bit RGB
    row = b"\x00" + b"\x30\x80\xff" * width
    return (
        sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(row * height, 6))
        + chunk(b"IEND", b"")
    )


def main() -> int:
    from wechat_mcp_publisher.core.client import get_client
    from wechat_mcp_publisher.core.exceptions import WeChatAPIError
    from wechat_mcp_publisher.tools.draft import create_news_draft

    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "smoke-cover.png"
        cover.write_bytes(_smoke_png())

        print("① 获取 access_token（内部自动，仅验证凭据与 IP 白名单）…")
        client = get_client()
        client._ensure_token()
        print("   ✓ token 获取成功")

        print("② 上传封面为永久素材…")
        material = client.upload_permanent_image(cover.name, cover.read_bytes())
        print(f"   ✓ thumb_media_id = {material.media_id}")

        print("③ 创建最小图文草稿…")
        result = create_news_draft(
            title="冒烟测试草稿（可删除）",
            content=f'<p>smoke test <img src="{cover}"></p>',
            cover=str(cover),
        )
        print(f"   ✓ 草稿已创建 media_id = {result['media_id']}")
        print("\n全部通过：请到公众号后台「草稿箱」核对后排版并删除该草稿。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WeChatAPIError as exc:
        print(f"\n✗ 微信接口错误：\n{exc}", file=sys.stderr)
        raise SystemExit(2)
    except FileNotFoundError as exc:
        print(f"\n✗ 文件错误：{exc}", file=sys.stderr)
        raise SystemExit(3)
