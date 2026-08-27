## MODIFIED Requirements

### Requirement: 创建图片消息草稿（newspic）
系统 SHALL 提供 `create_newspic_draft(title, content, images[], need_open_comment?, only_fans_can_comment?)` 工具：`content` 为必填纯文本说明（≤1000 字，非 HTML）；`images` 为 1~20 张本地图片路径或 http(s) URL；`need_open_comment` / `only_fans_can_comment` 为可选 bool 留言开关（解析规则见"可配置默认值三层解析"）。数量越界时返回明确错误。

#### Scenario: 正常创建
- **WHEN** 传入 title、纯文本说明、2 张存在的图片路径
- **THEN** 图片按序上传后草稿创建成功，返回 `media_id`

#### Scenario: 图片数量越界
- **WHEN** `images` 为空数组或多于 20 项
- **THEN** 工具返回说明数量限制的错误，不上传任何图片

## ADDED Requirements

### Requirement: 草稿字段预校验
创建工具 SHALL 在发起任何网络请求前完成字段校验，超限/非法即返回中文错误且 MUST NOT 上传图片或创建草稿：news 的 `title` ≤ 64 字、`digest` ≤ 120 字；newspic 的 `title` ≤ 20 字、`content` 必填且清洗后 ≤ 1000 字。恰好等于上限的输入合法。newspic 的 `content` 含 HTML 标记时 SHALL 自动清洗后使用（而非拒绝）：`<br>`/`</p>` 转换行、其余标签移除、HTML 实体反转义；清洗后的实际内容 SHALL 回显在返回值 `content` 字段。

#### Scenario: 图文标题超长拒绝
- **WHEN** news 的 `title` 为 65 字，其余参数合法
- **THEN** 工具返回含"当前 65 字 / 上限 64 字"说明的错误，未发起任何上传与草稿创建

#### Scenario: 图文摘要超长拒绝
- **WHEN** news 的 `digest` 为 121 字
- **THEN** 工具返回含当前字数与上限 120 字说明的错误（并提示留空可由微信自动截取正文），未发起网络请求

#### Scenario: 图文边界值通过
- **WHEN** news 的 `title` 恰为 64 字且 `digest` 恰为 120 字
- **THEN** 校验通过，继续正常创建流程

#### Scenario: 图片消息标题超长拒绝
- **WHEN** newspic 的 `title` 为 21 字
- **THEN** 工具返回含当前字数与上限 20 字说明的错误（并点明图片消息与图文上限不同），未上传任何图片

#### Scenario: 图片消息说明缺失拒绝
- **WHEN** newspic 的 `content` 为空、全空白、或清洗后无文字（仅有标签）
- **THEN** 工具返回"content 不能为空"错误，未上传任何图片

#### Scenario: 图片消息说明超长拒绝
- **WHEN** newspic 的 `content` 清洗后超过 1000 字
- **THEN** 工具返回含当前字数与上限 1000 字说明的错误，未上传任何图片

#### Scenario: 图片消息说明自动清洗
- **WHEN** newspic 的 `content` 为 `<p>这不是<b>纯文本</b></p>`
- **THEN** 草稿实际提交 `这不是纯文本\n`（标签移除、`</p>` 转换行），创建成功，返回值 `content` 字段回显清洗后内容

#### Scenario: 清洗含换行与实体
- **WHEN** newspic 的 `content` 为 `行一<br>行二 &amp; 更多`
- **THEN** 实际提交 `行一\n行二 & 更多`

#### Scenario: 普通文本中的尖括号不误伤
- **WHEN** newspic 的 `content` 为 `3<5 是真话`
- **THEN** 校验通过（非标签形态的 `<` 合法），内容原样提交
