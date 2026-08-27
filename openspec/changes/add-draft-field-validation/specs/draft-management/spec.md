## ADDED Requirements

### Requirement: 图文字段长度预校验
`create_news_draft` SHALL 在发起任何网络请求前校验：`title` 不超过 64 字、`digest` 不超过 120 字（按字符计）；超限时返回包含当前字数与上限的中文错误，且 MUST NOT 上传图片或创建草稿。恰好等于上限的输入合法。

#### Scenario: 标题超长拒绝
- **WHEN** `title` 为 65 字，其余参数合法
- **THEN** 工具返回含"当前 65 字 / 上限 64 字"说明的错误，未发起任何上传与草稿创建

#### Scenario: 摘要超长拒绝
- **WHEN** `digest` 为 121 字
- **THEN** 工具返回含当前字数与上限 120 字说明的错误（并提示留空可由微信自动截取正文），未发起网络请求

#### Scenario: 边界值通过
- **WHEN** `title` 恰为 64 字且 `digest` 恰为 120 字
- **THEN** 校验通过，继续正常创建流程
