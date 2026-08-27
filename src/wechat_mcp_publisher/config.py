"""配置管理：从环境变量或 .env 文件加载单账号凭据与行为开关。

启动时 fail-fast：凭据缺失、行为开关非法值，直接报错并给出指引（D9）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

APP_ID_ENV = "WECHAT_APP_ID"
APP_SECRET_ENV = "WECHAT_APP_SECRET"
NEED_OPEN_COMMENT_ENV = "WECHAT_NEED_OPEN_COMMENT"
ONLY_FANS_CAN_COMMENT_ENV = "WECHAT_ONLY_FANS_CAN_COMMENT"

# 留言开关内置默认（入参 > .env > 此处）
DEFAULT_NEED_OPEN_COMMENT = True
DEFAULT_ONLY_FANS_CAN_COMMENT = False

_TRUTHY = frozenset({"1", "true", "yes"})
_FALSY = frozenset({"0", "false", "no"})

_MISSING_GUIDE = """缺少微信公众号凭据：{missing} 未设置。

请任选一种方式配置：
  1. 在项目根目录创建 .env 文件（参考 .env.example）：
       {app_id_env}=你的AppID
       {app_secret_env}=你的AppSecret
  2. 或通过进程环境变量注入同名变量。

AppID/AppSecret 获取路径：微信公众平台 mp.weixin.qq.com → 设置与开发 → 基本配置。"""


class ConfigError(RuntimeError):
    """配置缺失或非法。"""


@dataclass(frozen=True)
class Config:
    """单账号凭据与行为开关（None = 未设置，走内置默认）。"""

    app_id: str
    app_secret: str
    need_open_comment: Optional[bool] = None
    only_fans_can_comment: Optional[bool] = None


def load_config() -> Config:
    """加载并校验配置；凭据缺失或开关非法值时抛出带指引的 ConfigError。"""
    load_dotenv()
    app_id = os.getenv(APP_ID_ENV, "").strip()
    app_secret = os.getenv(APP_SECRET_ENV, "").strip()

    missing = [
        name
        for name, value in ((APP_ID_ENV, app_id), (APP_SECRET_ENV, app_secret))
        if not value
    ]
    if missing:
        raise ConfigError(
            _MISSING_GUIDE.format(
                missing="、".join(missing),
                app_id_env=APP_ID_ENV,
                app_secret_env=APP_SECRET_ENV,
            )
        )
    return Config(
        app_id=app_id,
        app_secret=app_secret,
        need_open_comment=_parse_flag(NEED_OPEN_COMMENT_ENV),
        only_fans_can_comment=_parse_flag(ONLY_FANS_CAN_COMMENT_ENV),
    )


def resolve_flag(
    param: Optional[bool],
    env_value: Optional[bool],
    builtin: bool,
) -> bool:
    """三层优先级解析：用户入参 > .env 变量 > 内置默认。"""
    if param is not None:
        return param
    if env_value is not None:
        return env_value
    return builtin


def _parse_flag(env_name: str) -> Optional[bool]:
    """解析布尔环境变量；未设置返回 None，非法值抛 ConfigError。"""
    raw = os.getenv(env_name)
    if raw is None or not raw.strip():
        return None
    value = raw.strip().lower()
    if value in _TRUTHY:
        return True
    if value in _FALSY:
        return False
    raise ConfigError(
        f"环境变量 {env_name} 的值「{raw}」无法识别：仅接受 1/0/true/false（不区分大小写）"
    )
