## MODIFIED Requirements

### Requirement: 单账号配置加载
系统 SHALL 通过 `.env` 文件或进程环境变量读取唯一的账号凭据（`WECHAT_APP_ID`、`WECHAT_APP_SECRET`），MUST NOT 支持或要求在工具调用时传入凭据；同时 SHALL 解析可选行为开关 `WECHAT_NEED_OPEN_COMMENT` / `WECHAT_ONLY_FANS_CAN_COMMENT`（接受 1/0/true/false，不区分大小写；未设置视为未指定，非法值启动即报错并指明变量名与合法取值）。

#### Scenario: .env 加载
- **WHEN** 工作目录存在含有效凭据的 `.env` 文件
- **THEN** 启动时凭据被加载并校验通过

#### Scenario: 行为开关非法值拒绝启动
- **WHEN** `WECHAT_NEED_OPEN_COMMENT` 或 `WECHAT_ONLY_FANS_CAN_COMMENT` 被设置为白名单外的值（如 `maybe`）
- **THEN** 启动失败，错误信息指明变量名与合法取值（1/0/true/false）
