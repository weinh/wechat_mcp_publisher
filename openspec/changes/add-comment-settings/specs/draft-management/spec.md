## MODIFIED Requirements

### Requirement: 创建图片消息草稿（newspic）
系统 SHALL 提供 `create_newspic_draft(title, content, images[], need_open_comment?, only_fans_can_comment?)` 工具：`content` 为纯文本说明；`images` 为 1~20 张本地图片路径或 http(s) URL；`need_open_comment` / `only_fans_can_comment` 为可选 bool 留言开关（解析规则见"留言设置三层解析"）。数量越界时返回明确错误。

#### Scenario: 正常创建
- **WHEN** 传入 title、纯文本说明、2 张存在的图片路径
- **THEN** 图片按序上传后草稿创建成功，返回 `media_id`

#### Scenario: 图片数量越界
- **WHEN** `images` 为空数组或多于 20 项
- **THEN** 工具返回说明数量限制的错误，不上传任何图片

## ADDED Requirements

### Requirement: 留言设置三层解析
创建类工具（news / newspic）的留言开关 `need_open_comment`（内置默认开启，即 1）与 `only_fans_can_comment`（内置默认关闭，即 0）SHALL 按优先级解析：**用户入参 > `.env` 变量（`WECHAT_NEED_OPEN_COMMENT` / `WECHAT_ONLY_FANS_CAN_COMMENT`）> 内置默认**；提交给微信接口时 SHALL 转换为 0/1 整数。

#### Scenario: 入参覆盖一切
- **WHEN** 工具入参显式传入 `need_open_comment=false`，且 `.env` 设置了 `WECHAT_NEED_OPEN_COMMENT=1`
- **THEN** 提交微信的载荷中 `need_open_comment=0`

#### Scenario: .env 改写默认值
- **WHEN** 工具入参未传 `only_fans_can_comment`，且 `.env` 设置 `WECHAT_ONLY_FANS_CAN_COMMENT=1`
- **THEN** 提交微信的载荷中 `only_fans_can_comment=1`

#### Scenario: 内置默认兜底
- **WHEN** 工具入参未传且 `.env` 未设置两个留言变量
- **THEN** 提交微信的载荷中 `need_open_comment=1`、`only_fans_can_comment=0`

#### Scenario: 线上载荷为 0/1 整数
- **WHEN** 任一解析结果生效
- **THEN** 提交给 `draft/add` 的对应字段为整数 0 或 1，而非 bool
