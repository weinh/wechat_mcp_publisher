"""utils/helpers.py：HTML 内嵌图替换、图片加载校验、content 双形态。"""

from __future__ import annotations

import base64

import pytest

from wechat_mcp_publisher.utils.helpers import (
    MAX_IMAGE_SIZE,
    load_image,
    replace_inline_images,
    resolve_content,
    validate_image,
)

TINY_PNG = b"\x89PNG\r\n\x1a\nfakepngdata"


@pytest.fixture
def local_image(tmp_path):
    path = tmp_path / "pic.jpg"
    path.write_bytes(TINY_PNG)
    return str(path)


class TestReplaceInlineImages:
    def test_local_path_replaced(self, local_image):
        html = f'<p>正文</p><img src="{local_image}"><p>结尾</p>'
        out = replace_inline_images(html, lambda src: "https://mmbiz.qpic.cn/NEW.jpg")
        assert 'src="https://mmbiz.qpic.cn/NEW.jpg"' in out
        assert local_image not in out

    def test_remote_url_replaced(self):
        html = '<img src="https://example.com/a.png">'
        out = replace_inline_images(html, lambda src: "https://mmbiz.qpic.cn/NEW.jpg")
        assert out == '<img src="https://mmbiz.qpic.cn/NEW.jpg">'

    def test_weixin_domain_skipped(self):
        html = '<img src="https://mmbiz.qpic.cn/mmbiz/abc.jpeg">'
        called = []

        def uploader(src):
            called.append(src)
            return "REPLACED"

        out = replace_inline_images(html, uploader)
        assert out == html, "微信域名不应被改写"
        assert called == []

    def test_mp_weixin_domain_skipped(self):
        html = '<img src="https://mp.weixin.qq.com/x/y.png">'
        out = replace_inline_images(html, lambda src: pytest.fail("不应调用上传"))
        assert out == html

    def test_rest_of_html_untouched(self, local_image):
        html = (
            "<section style='color:red'><h1>标题</h1>"
            f"<img  alt='图' src=\"{local_image}\"  data-x='1'></section>"
        )
        out = replace_inline_images(html, lambda src: "W")
        assert out.startswith("<section style='color:red'><h1>标题</h1>")
        assert out.endswith("  data-x='1'></section>"), "除 src 外其余字节不变"
        assert "<img  alt='图' src=\"W\"  data-x='1'>" in out

    def test_single_quoted_src(self):
        html = "<img src='https://cdn.example.com/b.gif'>"
        out = replace_inline_images(html, lambda src: "W")
        assert out == "<img src='W'>"

    def test_data_uri_passed_to_uploader(self):
        b64 = base64.b64encode(b"imgbytes").decode()
        html = f'<img src="data:image/png;base64,{b64}">'
        seen = []

        def uploader(src):
            seen.append(src)
            return "W"

        out = replace_inline_images(html, uploader)
        assert out == '<img src="W">'
        assert seen and seen[0].startswith("data:image/png;base64,")

    def test_uploader_sees_original_src(self, local_image):
        seen = []
        replace_inline_images(f'<img src="{local_image}">', lambda s: (seen.append(s), "W")[1])
        assert seen == [local_image]


class TestLoadImage:
    def test_local_file(self, local_image):
        name, data = load_image(local_image)
        assert name == "pic.jpg"
        assert data == TINY_PNG

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_image("/nonexistent/path/pic.jpg")

    def test_data_uri(self):
        b64 = base64.b64encode(b"imgbytes").decode()
        name, data = load_image(f"data:image/png;base64,{b64}")
        assert name == "inline-image.png"
        assert data == b"imgbytes"

    def test_unsupported_ext_rejected(self, tmp_path):
        path = tmp_path / "pic.txt"
        path.write_bytes(b"text")
        with pytest.raises(ValueError, match="不支持"):
            load_image(str(path))

    def test_oversize_rejected(self, monkeypatch):
        # 直接调 validate_image 避免真造 10MB 文件
        with pytest.raises(ValueError, match="10MB"):
            validate_image("big.png", b"x" * (MAX_IMAGE_SIZE + 1))

    def test_empty_data_rejected(self):
        with pytest.raises(ValueError, match="为空"):
            validate_image("empty.jpg", b"")


class TestResolveContent:
    def test_file_path_read(self, tmp_path):
        path = tmp_path / "article.html"
        path.write_text("<p>来自文件</p>", encoding="utf-8")
        assert resolve_content(str(path)) == "<p>来自文件</p>"

    def test_plain_html_passthrough(self):
        assert resolve_content("<p>直接内容</p>") == "<p>直接内容</p>"
