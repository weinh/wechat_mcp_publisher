## 1. 修复与测试

- [x] 1.1 `core/client.py::_json_of` 解析前强制 `response.encoding = "utf-8"`；`tests/test_core/test_client.py` 新增复现用例：responses 以 `text/plain` 返回 UTF-8 中文 errmsg，断言不乱码
- [x] 1.2 `core/exceptions.py`：新增 `53402` 提示（建议换正常尺寸图片），`48001` 提示纠偏措辞；测试断言两处提示
- [x] 1.3 `examples/simple_usage.py`：坏 hex JPEG 替换为程序生成的 600×600 PNG（zlib+struct）
- [x] 1.4 48001 表述纠偏：`server/app.py` 服务器说明、README 已知限制段（改写为实测结论 + 53402 经验）
- [x] 1.5 全量测试 + 提交推送
