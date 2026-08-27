"""微信 API 错误统一定义与 errcode → 中文提示映射（D7）。

所有微信接口失败最终都转为 WeChatAPIError，工具层不再包装；
错误文本保证不含 access_token / AppSecret。
"""

from __future__ import annotations

from typing import Any, Mapping

# token 失效类错误码：触发强制刷新并重试一次（D8）
TOKEN_EXPIRED_CODES = frozenset({40001, 42001})

_ERRCODE_HINTS: Mapping[int, str] = {
    -1: "微信系统繁忙，请稍后重试",
    40001: "access_token 无效（系统会自动刷新重试一次）",
    40005: "不支持的媒体文件格式，图文内图片请使用 jpg/png/gif/bmp",
    40007: "media_id 无效，请确认素材或草稿 ID 是否正确",
    40009: "图片文件超过大小限制",
    40013: "AppID 无效，请检查 .env 中的 WECHAT_APP_ID",
    40125: "AppSecret 无效，请检查 .env 中的 WECHAT_APP_SECRET",
    40164: "调用方 IP 不在白名单中。请到公众号后台「设置与开发 → 基本配置 → IP 白名单」添加报错信息中给出的 IP 后重试",
    42001: "access_token 已过期（系统会自动刷新重试一次）",
    43101: "用户未关注或无法操作",
    45009: "接口调用次数超过每日配额，请次日再试",
    48001: "api unauthorized：当前账号无权调用该接口（部分接口需认证或特定账号类型；个人未认证订阅号的素材/草稿接口实测可用，遇到此码多为调用了受限接口）",
    50001: "用户未关注公众号",
    53401: "该草稿状态不支持此操作",
    53402: "封面裁剪失败：请改用正常尺寸的图片（太小或比例异常的图无法裁出封面，实测 1×1 会挂、600×600 可过）",
    53404: "草稿不存在",
    200001: "内容含有违反公众平台规定的风险词或敏感信息",
}

# 错误信息中需要脱敏的键（防 token/secret 意外进入文本）
_SENSITIVE_KEYS = ("access_token", "app_secret", "secret")


class WeChatAPIError(Exception):
    """微信接口返回非 0 errcode 时抛出。"""

    def __init__(self, errcode: int, errmsg: str) -> None:
        self.errcode = errcode
        self.errmsg = _sanitize(errmsg)
        message = f"微信接口错误 {self.errcode}：{self.errmsg}"
        hint = _ERRCODE_HINTS.get(errcode)
        if hint:
            message = f"{message}\n提示：{hint}"
        super().__init__(message)


class WeChatResponseError(WeChatAPIError):
    """响应不是合法 JSON（网关异常、限流页等）。"""

    def __init__(self, detail: str) -> None:
        super().__init__(-1, f"微信接口返回了无法解析的响应：{detail[:200]}")


def raise_for_code(payload: Mapping[str, Any]) -> None:
    """按微信统一约定检查 errcode，非 0 即抛 WeChatAPIError。"""
    errcode = int(payload.get("errcode", 0) or 0)
    if errcode != 0:
        raise WeChatAPIError(errcode, str(payload.get("errmsg", "")))


def _sanitize(text: str) -> str:
    """抹掉可能混入错误文本里的敏感值（尽力而为）。"""
    for key in _SENSITIVE_KEYS:
        text = text.replace(key, "***")
    return text
