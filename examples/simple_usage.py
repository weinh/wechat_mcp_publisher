"""真机冒烟 / 用法演示：token → 图片上传 → 建最小草稿。

用途：
- 平时：直接阅读本文件了解工具链怎么串
- 认证账号到位后：`uv run python examples/simple_usage.py` 逐步验证真机链路

预期失败点（按顺序暴露）：
  40164  调用方 IP 不在白名单 → 去公众号后台加白名单后重跑
  48001  个人未认证订阅号无权调用素材/草稿接口 → 需已认证账号
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

# 造一张最小 jpg（1x1 像素）用于冒烟，可用真实图片路径替换
_TINY_JPEG = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100ffc4001f0000010501010101010100000000000000000102030405060708090a0bffc400b5100002010303020403050504040000017d01020300041105122131410613516107227114328191a1082342b1c11552d1f02433627282090a161718191a25262728292a3435363738393a434445464748494a535455565758595a636465666768696a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffda0008010100003f00fbfa28a2803ffd9"
)


def main() -> int:
    from wechat_mcp_publisher.core.client import get_client
    from wechat_mcp_publisher.core.exceptions import WeChatAPIError
    from wechat_mcp_publisher.tools.draft import create_news_draft

    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "smoke-cover.jpg"
        cover.write_bytes(_TINY_JPEG)

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
