"""config.py：默认值三层解析（留言开关 / 作者）与 .env 变量解析。"""

from __future__ import annotations

import pytest

from wechat_mcp_publisher.config import (
    Config,
    ConfigError,
    load_config,
    resolve_setting,
)


class TestResolveSetting:
    def test_param_wins_over_everything(self):
        assert resolve_setting(True, False, False) is True
        assert resolve_setting(False, True, True) is False

    def test_env_overrides_builtin(self):
        assert resolve_setting(None, True, False) is True
        assert resolve_setting(None, False, True) is False

    def test_builtin_fallback(self):
        assert resolve_setting(None, None, True) is True
        assert resolve_setting(None, None, False) is False

    def test_string_tiers(self):
        assert resolve_setting("入参", ".env", "") == "入参"
        assert resolve_setting(None, ".env", "") == ".env"
        assert resolve_setting(None, None, "") == ""
        # 空字符串是显式入参，能压过 .env
        assert resolve_setting("", ".env", "") == ""


class TestLoadConfigFlags:
    def test_unset_flags_are_none(self, monkeypatch):
        monkeypatch.setenv("WECHAT_APP_ID", "id")
        monkeypatch.setenv("WECHAT_APP_SECRET", "secret")
        monkeypatch.delenv("WECHAT_NEED_OPEN_COMMENT", raising=False)
        monkeypatch.delenv("WECHAT_ONLY_FANS_CAN_COMMENT", raising=False)
        monkeypatch.delenv("WECHAT_AUTHOR", raising=False)
        cfg = load_config()
        assert cfg.need_open_comment is None
        assert cfg.only_fans_can_comment is None
        assert cfg.author is None

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("老王", "老王"),
            ("  带空白  ", "带空白"),
            ("", None),   # 空白视为未设置
            ("   ", None),
        ],
    )
    def test_author_parsing(self, monkeypatch, raw, expected):
        monkeypatch.setenv("WECHAT_APP_ID", "id")
        monkeypatch.setenv("WECHAT_APP_SECRET", "secret")
        monkeypatch.setenv("WECHAT_AUTHOR", raw)
        assert load_config().author is expected

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("1", True), ("true", True), ("TRUE", True), ("Yes", True),
            ("0", False), ("false", False), ("FALSE", False), ("No", False),
            (" true ", True),  # 容忍首尾空白
        ],
    )
    def test_valid_values(self, monkeypatch, raw, expected):
        monkeypatch.setenv("WECHAT_APP_ID", "id")
        monkeypatch.setenv("WECHAT_APP_SECRET", "secret")
        monkeypatch.setenv("WECHAT_NEED_OPEN_COMMENT", raw)
        assert load_config().need_open_comment is expected

    @pytest.mark.parametrize("raw", ["maybe", "2", "on", "开"])
    def test_invalid_value_raises(self, monkeypatch, raw):
        monkeypatch.setenv("WECHAT_APP_ID", "id")
        monkeypatch.setenv("WECHAT_APP_SECRET", "secret")
        monkeypatch.setenv("WECHAT_ONLY_FANS_CAN_COMMENT", raw)
        with pytest.raises(ConfigError, match="WECHAT_ONLY_FANS_CAN_COMMENT"):
            load_config()

    def test_missing_credentials_still_priority(self, monkeypatch):
        # 隔离本地 .env 文件（仓库根有占位 .env，会被 load_dotenv 读走）
        monkeypatch.setattr(
            "wechat_mcp_publisher.config.load_dotenv", lambda *a, **k: False
        )
        monkeypatch.delenv("WECHAT_APP_ID", raising=False)
        monkeypatch.delenv("WECHAT_APP_SECRET", raising=False)
        with pytest.raises(ConfigError, match="WECHAT_APP_ID"):
            load_config()
