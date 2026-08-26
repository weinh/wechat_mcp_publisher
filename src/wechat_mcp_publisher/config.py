"""配置管理：从环境变量或 .env 文件加载单账号凭据。

启动时 fail-fast：凭据缺失直接报错并给出设置指引（D9）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

APP_ID_ENV = "WECHAT_APP_ID"
APP_SECRET_ENV = "WECHAT_APP_SECRET"

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
    """单账号凭据。"""

    app_id: str
    app_secret: str


def load_config() -> Config:
    """加载并校验配置；缺失时抛出带指引的 ConfigError。"""
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
    return Config(app_id=app_id, app_secret=app_secret)
