## Why

微信 `draft/add` 对图文的标题（≤64 字）与摘要（≤120 字）有硬性上限，超限要到提交后才收到接口报错；LLM 生成的标题/摘要容易越界，应在工具入口预校验、立即给出中文错误，避免白白上传图片后失败。

## What Changes

- `create_news_draft` 入口新增长度预校验：`title` ≤ 64 字、`digest` ≤ 120 字
- `create_newspic_draft` 入口新增预校验：`title` ≤ 20 字（图片消息上限，与图文不同）；`content` **变为必填**、清洗后 ≤ 1000 字
- `content` 若带 HTML 标记则**自动清洗**而非拒绝：标签移除、`<br>`/`</p>` 转换行、HTML 实体（`&amp;` 等）反转义；仅有标签没有文字视为空；实际使用的内容回显在返回值 `content` 字段
- 超限时抛出含"当前字数/上限"的中文错误，且**不发起任何网络请求**（不上传图片、不建草稿）
- 边界值（恰好 64/120、20/1000 字）合法
- docstring 标注各字段上限

**BREAKING**：`create_newspic_draft` 的 `content` 从可选变为必填（签名调整为 `title, content, images`），旧调用不传 content 将被 schema 拒绝——赶在 0.2.0 发版前落地。

## Capabilities

### New Capabilities
（无）

### Modified Capabilities
- `draft-management`: 新增"草稿字段预校验"要求（news 长度 + newspic 长度/必填/纯文本）；newspic 工具签名要求更新（content 必填）

## Impact

- `tools/draft.py`：上限常量 + 两个校验函数（在 `get_client()` 之前调用）
- 测试：超长拒绝（无网络副作用）、边界通过、HTML 拒绝、含 `<` 的普通文本通过
- 不改配置、不改线上载荷（微信接口本身仍会再校验一道）
