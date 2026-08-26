"""stdio 启动入口：uv run python -m wechat_mcp_publisher

启动时 fail-fast 校验配置（缺失凭据直接退出并给出指引，不进入服务循环）。
错误输出走 stderr——stdout 是 stdio 协议通道，不可污染。
"""

from __future__ import annotations

import sys

from .config import ConfigError, load_config
from .server.app import server


def main() -> None:
    try:
        load_config()
    except ConfigError as exc:
        print(f"启动失败：{exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
