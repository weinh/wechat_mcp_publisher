## 1. 配置层

- [x] 1.1 `config.py`：`Config` 增加 `need_open_comment` / `only_fans_can_comment` 可选字段（None=未设置）；`load_config()` 解析两个新环境变量（白名单 1/0/true/false，非法值 ConfigError 指明变量与合法值）；新增纯函数 `resolve_flag(param, env_value, builtin)`

## 2. 工具层

- [x] 2.1 `core/client.py`：`WeChatClient` 暴露只读 `config` 属性
- [x] 2.2 `tools/draft.py`：两个创建工具增加 `need_open_comment: bool | None = None` / `only_fans_can_comment: bool | None = None` 参数与中文 docstring；经 `resolve_flag` 三层解析后以 `int()` 转 0/1 写入 article 载荷
- [x] 2.3 `.env.example` 增加两个可选项说明；README 补充留言开关用法

## 3. 测试

- [x] 3.1 `tests/test_core/`：`resolve_setting` 矩阵 + 非法 env 值报错 + 白名单解析
- [x] 3.2 `tests/test_tools/`：入参覆盖 / .env 覆盖默认 / 内置兜底三场景对两个工具验证，线上载荷为 0/1 整数

## 4. 作者名（扩展需求）

- [x] 4.1 `config.py`：`Config.author` 可选字段 + `WECHAT_AUTHOR` 解析（去空白，空白=未设置）；`resolve_flag` 通用化为 `resolve_setting`
- [x] 4.2 `tools/draft.py`：`create_news_draft` 的 `author` 改为 `Optional[str]`，走三层解析（空字符串为显式入参）；newspic 不加作者字段
- [x] 4.3 测试与文档：作者三层矩阵（含空串覆盖）+ newspic 无 author 断言；`.env.example` / README 更新
