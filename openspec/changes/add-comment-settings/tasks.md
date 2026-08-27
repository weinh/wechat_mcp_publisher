## 1. 配置层

- [x] 1.1 `config.py`：`Config` 增加 `need_open_comment` / `only_fans_can_comment` 可选字段（None=未设置）；`load_config()` 解析两个新环境变量（白名单 1/0/true/false，非法值 ConfigError 指明变量与合法值）；新增纯函数 `resolve_flag(param, env_value, builtin)`

## 2. 工具层

- [x] 2.1 `core/client.py`：`WeChatClient` 暴露只读 `config` 属性
- [x] 2.2 `tools/draft.py`：两个创建工具增加 `need_open_comment: bool | None = None` / `only_fans_can_comment: bool | None = None` 参数与中文 docstring；经 `resolve_flag` 三层解析后以 `int()` 转 0/1 写入 article 载荷
- [x] 2.3 `.env.example` 增加两个可选项说明；README 补充留言开关用法

## 3. 测试

- [x] 3.1 `tests/test_core/`：`resolve_flag` 矩阵 + 非法 env 值报错 + 白名单解析
- [x] 3.2 `tests/test_tools/`：入参覆盖 / .env 覆盖默认 / 内置兜底三场景对两个工具验证，线上载荷为 0/1 整数
