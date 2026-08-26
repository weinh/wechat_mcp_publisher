## ADDED Requirements

### Requirement: token 自动获取
系统 SHALL 在首次需要调用微信 API 时通过 `stable_token` 接口自动获取 access_token，全程无需 LLM 或用户手动介入。

#### Scenario: 首次调用自动取 token
- **WHEN** 服务器启动后第一次执行任一业务工具
- **THEN** 系统先调用 `stable_token` 获取 token，再执行业务请求，工具结果中不体现 token 获取过程

### Requirement: token 缓存与提前刷新
系统 SHALL 将 token 缓存在进程内存中，在剩余有效期不足 5 分钟时于下次调用前自动刷新；有效期内多次业务调用 MUST NOT 重复获取 token。

#### Scenario: 有效期内复用
- **WHEN** token 获取成功后 1 分钟内连续执行 3 次业务工具调用
- **THEN** `stable_token` 接口仅被调用 1 次

#### Scenario: 临近过期自动刷新
- **WHEN** 缓存的 token 剩余有效期小于 5 分钟，此时发起业务调用
- **THEN** 系统先刷新 token 再执行业务调用

### Requirement: token 失效自愈重试
业务请求遇 `40001` 或 `42001`（token 失效）时，系统 SHALL 强制刷新 token 并重试该请求恰好一次；重试仍失败则按可读错误返回。

#### Scenario: 失效后自愈
- **WHEN** 业务请求返回 `40001`
- **THEN** 系统丢弃缓存 token、重新获取并重试原请求，重试成功时工具正常返回

#### Scenario: 重试一次后失败
- **WHEN** 刷新后重试的请求仍返回 `40001`
- **THEN** 工具返回可读错误，不再发起第三次尝试

### Requirement: token 对外不可见
系统 MUST NOT 将 token 获取或管理能力注册为 MCP 工具，MUST NOT 在任何工具的参数、返回值或错误信息中暴露 token。

#### Scenario: 工具列表不含 token 工具
- **WHEN** MCP 客户端调用 `tools/list`
- **THEN** 返回的工具集合中不存在任何与 token 获取/刷新相关的工具
