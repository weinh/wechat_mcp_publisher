## 1. 实现与测试

- [x] 1.1 `tools/draft.py`：新增 `NEWS_TITLE_MAX_CHARS=64` / `NEWS_DIGEST_MAX_CHARS=120` 与 `_validate_news_fields()`，在 `get_client()` 之前调用；docstring 标注上限
- [x] 1.2 `tests/test_tools/test_draft.py`：标题 65 字拒绝、摘要 121 字拒绝（均断言零上传零建草稿）、64/120 边界通过

## 2. newspic 校验（扩展需求）

- [x] 2.1 `create_newspic_draft` 签名调整为 `(title, content, images)`，content 必填；新增 `NEWSPIC_TITLE_MAX_CHARS=20` / `NEWSPIC_CONTENT_MAX_CHARS=1000` 与 `_validate_newspic_fields()`（含 HTML 标记检测 `</?[a-zA-Z][^>]*>`），在图片数量校验与 `get_client()` 之前执行
- [x] 2.2 既有 newspic 测试适配新签名；新增：标题 21 字拒绝、content 空/1001 字/含 HTML 拒绝（均断言零上传零建草稿）、20/1000 边界通过、"3<5" 纯文本不误伤
