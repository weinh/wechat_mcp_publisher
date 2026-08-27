## Why

微信 `draft/add` 对图文的标题（≤64 字）与摘要（≤120 字）有硬性上限，超限要到提交后才收到接口报错；LLM 生成的标题/摘要容易越界，应在工具入口预校验、立即给出中文错误，避免白白上传图片后失败。

## What Changes

- `create_news_draft` 入口新增长度预校验：`title` ≤ 64 字、`digest` ≤ 120 字
- 超限时抛出含"当前字数/上限"的中文错误，且**不发起任何网络请求**（不上传图片、不建草稿）
- 边界值（恰好 64/120 字）合法
- docstring 标注两个字段的上限

## Capabilities

### New Capabilities
（无）

### Modified Capabilities
- `draft-management`: 新增"图文字段长度预校验"要求（newspic 不在本次范围）

## Impact

- `tools/draft.py`：两个上限常量 + 校验函数（在 `get_client()` 之前调用）
- 测试：超长拒绝（无网络副作用）、边界通过
- 不改配置、不改线上载荷（微信接口本身仍会再校验一道）
