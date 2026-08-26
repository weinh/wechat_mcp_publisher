## ADDED Requirements

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
系统 SHALL 提供 `create_newspic_draft(title, content, images[])` 工具：`content` 为纯文本说明；`images` 为 1~20 张本地图片路径或 http(s) URL。数量越界时返回明确错误。

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
