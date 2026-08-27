# draft-management Specification

## Purpose

提供微信公众号草稿的完整管理工具集：创建图文（news）草稿、创建图片消息（newspic）草稿、分页查询草稿列表、查询草稿详情与删除草稿。

## Requirements

### Requirement: 创建图文草稿（news）
系统 SHALL 提供 `create_news_draft(title, content, cover, author?, digest?, ...)` 工具：`content` 接受 HTML 字符串或本地 `.html` 文件路径（文件存在即视为路径，否则视为内容）；`cover` 接受本地路径或 http(s) URL；内部完成内嵌图替换与封面上传后调用 `draft/add`，成功时返回草稿 `media_id`。

#### Scenario: 最小参数成功
- **WHEN** 传入 title、合法 HTML 内容、存在的封面图片路径
- **THEN** 草稿创建成功，工具返回新草稿的 `media_id`

#### Scenario: content 为文件路径
- **WHEN** `content` 传入一个存在的 `.html` 文件路径
- **THEN** 系统读取文件内容作为正文，流程与直接传 HTML 一致

#### Scenario: 缺少必填参数
- **WHEN** 未提供 title 或 cover
- **THEN** 工具返回参数校验错误，不发起微信请求

### Requirement: 创建图片消息草稿（newspic）
系统 SHALL 提供 `create_newspic_draft(title, content, images[], need_open_comment?, only_fans_can_comment?)` 工具：`content` 为纯文本说明；`images` 为 1~20 张本地图片路径或 http(s) URL；`need_open_comment` / `only_fans_can_comment` 为可选 bool 留言开关（解析规则见“留言设置三层解析”）。数量越界时返回明确错误。

#### Scenario: 正常创建
- **WHEN** 传入 title、纯文本说明、2 张存在的图片路径
- **THEN** 图片按序上传后草稿创建成功，返回 `media_id`

#### Scenario: 图片数量越界
- **WHEN** `images` 为空数组或多于 20 项
- **THEN** 工具返回说明数量限制的错误，不上传任何图片

### Requirement: 草稿列表查询
系统 SHALL 提供 `list_drafts` 工具，返回草稿的分页列表，每项至少包含 `media_id`、标题与更新时间。

#### Scenario: 查询列表
- **WHEN** 账号下存在草稿，调用 `list_drafts`
- **THEN** 返回草稿列表及总数，可翻页

### Requirement: 草稿详情查询
系统 SHALL 提供 `get_draft(media_id)` 工具，返回指定草稿的完整内容；草稿不存在时返回可读错误。

#### Scenario: 查询存在的草稿
- **WHEN** 传入有效 `media_id`
- **THEN** 返回该草稿的标题、正文等全部字段

#### Scenario: 草稿不存在
- **WHEN** 传入的 `media_id` 不存在
- **THEN** 工具返回包含微信错误码说明的可读错误

### Requirement: 删除草稿
系统 SHALL 提供 `delete_draft(media_id)` 工具删除指定草稿；删除草稿 MUST NOT 连带删除其引用的永久素材（微信行为，系统不做额外清理）。

#### Scenario: 删除成功
- **WHEN** 传入有效 `media_id` 且删除成功
- **THEN** 工具返回删除成功标识

#### Scenario: 删除不存在的草稿
- **WHEN** 传入的 `media_id` 不存在
- **THEN** 工具返回可读错误而非静默成功

### Requirement: 可配置默认值三层解析
创建类工具的可配置字段——留言开关 `need_open_comment`（内置默认开启，即 1）与 `only_fans_can_comment`（内置默认关闭，即 0，news/newspic 均适用），作者名 `author`（内置默认空串，仅 news 适用，微信 newspic 结构无作者字段）——SHALL 按优先级解析：**用户入参 > `.env` 变量（`WECHAT_NEED_OPEN_COMMENT` / `WECHAT_ONLY_FANS_CAN_COMMENT` / `WECHAT_AUTHOR`）> 内置默认**；留言开关提交给微信接口时 SHALL 转换为 0/1 整数。

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
- **WHEN** 任一留言开关解析结果生效
- **THEN** 提交给 `draft/add` 的对应字段为整数 0 或 1，而非 bool

#### Scenario: 作者名三层解析
- **WHEN** `create_news_draft` 未传 `author` 且 `.env` 设置 `WECHAT_AUTHOR=公众号编辑`
- **THEN** 载荷 `author="公众号编辑"`；入参传 `author="特邀作者"` 时以入参为准；入参传空字符串时载荷 `author=""`（显式清空 `.env` 默认）

#### Scenario: 作者字段仅 news 适用
- **WHEN** `create_newspic_draft` 创建草稿
- **THEN** 载荷不包含 `author` 字段（微信图片消息结构无作者字段）
