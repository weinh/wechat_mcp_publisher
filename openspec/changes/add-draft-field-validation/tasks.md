## 1. 实现与测试

- [x] 1.1 `tools/draft.py`：新增 `NEWS_TITLE_MAX_CHARS=64` / `NEWS_DIGEST_MAX_CHARS=120` 与 `_validate_news_fields()`，在 `get_client()` 之前调用；docstring 标注上限
- [x] 1.2 `tests/test_tools/test_draft.py`：标题 65 字拒绝、摘要 121 字拒绝（均断言零上传零建草稿）、64/120 边界通过
