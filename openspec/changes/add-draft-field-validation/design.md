## Context

微信图文标题上限 64 字、摘要上限 120 字（按字符计，中文 1 字）。当前超限要等 `draft/add` 返回错误，此时封面/内嵌图已全部上传完毕，浪费素材与调用。

## Goals / Non-Goals

**Goals:** 工具入口预校验 title/digest 长度，超限即中文报错，零网络副作用。

**Non-Goals:** 不校验 news 的 HTML 正文长度（微信限制宽松且按字节，暂无必要）；不剥离 HTML 而是整体拒绝（宁报错不静默改用户内容）。

## Decisions

**D1：字数用 `len(str)`（码点数），常量放 `tools/draft.py`**
微信按"字"计数，中文/字母均计 1；`len()` 即码点数，emoji 代理对误差可接受。上限常量 `NEWS_TITLE_MAX_CHARS=64` / `NEWS_DIGEST_MAX_CHARS=120` / `NEWSPIC_TITLE_MAX_CHARS=20` / `NEWSPIC_CONTENT_MAX_CHARS=1000` 与工具同文件，紧邻使用处。图片消息标题上限 20 字与图文 64 字不同，报错文案中显式点出。

**D2：校验在 `get_client()` 之前执行**
保证超限路径零网络副作用（规格场景断言不上传、不建草稿）；与既有的"title 不能为空"校验放同一段。

**D3：报错信息带当前字数与上限，不静默截断/剥离**
静默处理会让 LLM 以为原内容生效；报错让它自己改。摘要报错附"留空则微信自动截取正文"，HTML 拒绝报错附"富文本请改用 create_news_draft"。

**D4：newspic `content` 必填 + 纯文本检测用标签正则**
签名调整为 `(title, content, images)`，content 缺失/空白即报错。HTML 检测用 `</?[a-zA-Z][^>]*>`——只认"像标签"的片段，普通文本里的 `<`（如 "3<5"）不误伤；不检 HTML 实体（`&nbsp;` 等，误伤率高于收益）。**BREAKING**：content 原为可选，升 minor 版本（0.2.0）一并发布。

## Risks / Trade-offs

- [微信实际限制若调整] → 常量集中两处，改一行即可；接口侧仍是最终裁决
- [空 digest] → 空串长度 0，天然通过（语义=自动截取正文），无需特判

## Migration Plan

纯新增校验，无迁移；旧行为中"超长传给微信报错"变为"本地报错"，对正确调用无影响。

## Open Questions

（无）
