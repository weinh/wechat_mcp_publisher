## ADDED Requirements

### Requirement: 永久素材图片上传
系统 SHALL 支持将本地图片文件上传为微信永久素材（`material/add_material`，type=image），返回 `media_id`；用于图文封面与 newspic 图片消息。输入为 http(s) URL 时 SHALL 先下载再上传。上传前 MUST 校验文件存在，不存在时报错且不发起任何后续请求。

#### Scenario: 本地文件上传为封面
- **WHEN** 给定存在的本地图片路径执行 `create_news_draft`
- **THEN** 图片经 `add_material` 上传，返回的 `thumb_media_id` 用于草稿提交

#### Scenario: 远程 URL 下载后上传
- **WHEN** 封面参数为 http(s) URL
- **THEN** 系统下载该图片并上传为永久素材，流程与本地文件一致

#### Scenario: 文件不存在
- **WHEN** 给定的图片路径在文件系统中不存在
- **THEN** 工具立即返回明确指出该路径的错误，不发起上传，不创建草稿

### Requirement: 图文正文内嵌图上传与替换
创建图文草稿时，系统 SHALL 扫描正文 HTML 中的全部 `<img>` 标签：本地路径与 http(s) 外链经 `media/uploadimg` 上传后，把 `src` 替换为返回的微信 URL；src 为 data URI 时解码后上传替换；src 已是微信域名（`mmbiz.qpic.cn` 或 `mp.weixin.qq.com`）时跳过不处理。除 `src` 值外，HTML 其余部分 MUST NOT 被改写。

#### Scenario: 本地路径内嵌图替换
- **WHEN** 正文 HTML 含 `<img src="/local/pic.jpg">` 且文件存在
- **THEN** 该图经 `uploadimg` 上传，src 被替换为微信返回的 URL，其余 HTML 原样保留

#### Scenario: 外链内嵌图替换
- **WHEN** 正文 HTML 含 `<img src="https://example.com/pic.png">`
- **THEN** 系统下载该图、上传 `uploadimg` 并替换 src

#### Scenario: 微信域名跳过
- **WHEN** 正文 HTML 含 `<img src="https://mmbiz.qpic.cn/mmbiz/xxx.jpeg">`
- **THEN** 该 img 不触发任何上传，src 保持不变

### Requirement: 图片格式与大小校验
上传前系统 SHALL 校验图片为微信支持的格式（jpg/png 等）且不超过接口限制（10MB），不满足时返回指明具体原因的错误。

#### Scenario: 超大图片
- **WHEN** 待上传图片大于 10MB
- **THEN** 工具返回说明大小限制的错误，不上传该图

#### Scenario: 不支持的格式
- **WHEN** 待上传文件扩展名不在支持列表内
- **THEN** 工具返回说明支持格式的错误，不上传该图

### Requirement: newspic 多图按序上传
创建图片消息草稿时，系统 SHALL 按传入顺序逐张上传图片并按同序组装 `image_list`；任一图片上传失败时 MUST NOT 创建草稿。

#### Scenario: 多图保序
- **WHEN** `create_newspic_draft` 传入 3 张本地图片路径
- **THEN** 三张图按传入顺序出现在草稿的 `image_list` 中

#### Scenario: 中途失败不建草稿
- **WHEN** 多图上传过程中第二张因网络错误失败
- **THEN** 工具返回错误信息，不调用 `draft/add`
