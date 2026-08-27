## MODIFIED Requirements

### Requirement: 工具错误可读且不泄露凭据
工具失败时 SHALL 返回包含错误原因与处置提示的中文错误信息；任何错误信息、日志或返回值中 MUST NOT 出现 access_token 或 AppSecret；微信接口返回的中文 errmsg（含 `text/plain` 无 charset 响应）SHALL 被正确按 UTF-8 解码，MUST NOT 出现编码乱码。

#### Scenario: 微信侧错误透传为可读信息
- **WHEN** 任一工具调用导致微信 API 返回错误码
- **THEN** 工具返回该错误码对应的中文说明及处置提示，且不含 token/secret

#### Scenario: text/plain 响应的中文 errmsg 不乱码
- **WHEN** 微信接口以 `Content-Type: text/plain`（无 charset）返回 UTF-8 编码的中文 errmsg（如 53402 封面裁剪失败）
- **THEN** 工具错误信息中的 errmsg 为可读中文，而非形如 `å°é¢è£åª` 的乱码

#### Scenario: 敏感值不泄露
- **WHEN** 工具因任何原因失败
- **THEN** 错误文本与日志中不包含 access_token 与 AppSecret 的值
