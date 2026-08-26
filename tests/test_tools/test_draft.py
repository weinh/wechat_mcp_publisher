"""tools/draft.py 与 tools/material.py：编排逻辑（monkeypatch core 客户端）。"""

from __future__ import annotations

import pytest

from wechat_mcp_publisher.core.exceptions import WeChatAPIError
from wechat_mcp_publisher.core.models import DraftPage, DraftSummary, MaterialImage
from wechat_mcp_publisher.tools import draft as draft_tools
from wechat_mcp_publisher.tools import material as material_tools

TINY_JPG = b"\xff\xd8\xff\xe0fakejpg"


class FakeClient:
    def __init__(self):
        self.inline_uploads: list[str] = []
        self.permanent_uploads: list[str] = []
        self.drafts_created: list[list[dict]] = []
        self.fail_permanent_at: int | None = None  # 第 N 次永久上传时失败（0 起）

    def upload_inline_image(self, filename: str, data: bytes) -> str:
        self.inline_uploads.append(filename)
        return f"https://mmbiz.qpic.cn/inline/{len(self.inline_uploads)}.jpg"

    def upload_permanent_image(self, filename: str, data: bytes) -> MaterialImage:
        if self.fail_permanent_at is not None and len(self.permanent_uploads) == self.fail_permanent_at:
            raise WeChatAPIError(-1, "上传失败（模拟）")
        self.permanent_uploads.append(filename)
        return MaterialImage(
            media_id=f"PERM-{len(self.permanent_uploads)}",
            url=f"https://mmbiz.qpic.cn/perm/{len(self.permanent_uploads)}.jpg",
        )

    def create_draft(self, articles: list[dict]) -> str:
        self.drafts_created.append(articles)
        return "DRAFT-ID-1"

    def list_drafts(self, offset=0, count=20, *, no_content=True) -> DraftPage:
        return DraftPage(
            total=2,
            offset=offset,
            items=[
                DraftSummary(media_id="D1", title="草稿一", update_time=100),
                DraftSummary(media_id="D2", title="草稿二", update_time=200),
            ],
        )

    def get_draft(self, media_id: str) -> dict:
        return {"news_item": [{"title": "草稿一", "content": "<p>hi</p>"}]}

    def delete_draft(self, media_id: str) -> bool:
        return True


@pytest.fixture
def fake(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(draft_tools, "get_client", lambda: client)
    monkeypatch.setattr(material_tools, "get_client", lambda: client)
    return client


@pytest.fixture
def cover(tmp_path):
    path = tmp_path / "cover.jpg"
    path.write_bytes(TINY_JPG)
    return str(path)


@pytest.fixture
def inline_image(tmp_path):
    path = tmp_path / "inline.jpg"
    path.write_bytes(TINY_JPG)
    return str(path)


class TestCreateNewsDraft:
    def test_minimal_success(self, fake, cover, inline_image):
        html = f'<p>正文</p><img src="{inline_image}">'
        result = draft_tools.create_news_draft("标题", html, cover)

        assert result == {
            "media_id": "DRAFT-ID-1",
            "title": "标题",
            "cover_url": "https://mmbiz.qpic.cn/perm/1.jpg",
        }
        article = fake.drafts_created[0][0]
        assert article["thumb_media_id"] == "PERM-1"
        assert f"https://mmbiz.qpic.cn/inline/1.jpg" in article["content"], "内嵌图 src 应已替换"
        assert "article_type" not in article, "图文草稿不携带 article_type"

    def test_content_as_file_path(self, fake, cover, tmp_path):
        article = tmp_path / "article.html"
        article.write_text("<p>来自文件的内容</p>", encoding="utf-8")
        result = draft_tools.create_news_draft("文件标题", str(article), cover)
        assert result["media_id"] == "DRAFT-ID-1"
        assert fake.drafts_created[0][0]["content"] == "<p>来自文件的内容</p>"

    def test_missing_title_no_api_calls(self, fake, cover):
        with pytest.raises(ValueError, match="title"):
            draft_tools.create_news_draft("  ", "<p>x</p>", cover)
        assert fake.drafts_created == [] and fake.permanent_uploads == []

    def test_missing_cover_no_api_calls(self, fake):
        with pytest.raises(FileNotFoundError, match="不存在"):
            draft_tools.create_news_draft("标题", "<p>x</p>", "/no/such/cover.jpg")
        assert fake.drafts_created == [] and fake.permanent_uploads == []

    def test_empty_content_rejected(self, fake, cover):
        with pytest.raises(ValueError, match="content"):
            draft_tools.create_news_draft("标题", "   ", cover)
        assert fake.drafts_created == []


class TestCreateNewspicDraft:
    def test_images_order_preserved(self, fake, tmp_path):
        paths = []
        for i in range(3):
            p = tmp_path / f"img{i}.jpg"
            p.write_bytes(TINY_JPG)
            paths.append(str(p))

        result = draft_tools.create_newspic_draft("多图", paths, content="说明文字")

        assert result["image_count"] == 3
        article = fake.drafts_created[0][0]
        assert article["article_type"] == "newspic"
        assert article["content"] == "说明文字"
        image_list = article["image_info"]["image_list"]
        assert [item["image_media_id"] for item in image_list] == ["PERM-1", "PERM-2", "PERM-3"]

    def test_zero_images_rejected_before_upload(self, fake):
        with pytest.raises(ValueError, match="1~20"):
            draft_tools.create_newspic_draft("无图", [])
        assert fake.permanent_uploads == [], "数量越界时不应上传任何图片"

    def test_too_many_images_rejected(self, fake):
        with pytest.raises(ValueError, match="1~20"):
            draft_tools.create_newspic_draft("超量", [f"/tmp/{i}.jpg" for i in range(21)])

    def test_upload_failure_no_draft_created(self, fake, tmp_path):
        paths = []
        for i in range(2):
            p = tmp_path / f"img{i}.jpg"
            p.write_bytes(TINY_JPG)
            paths.append(str(p))
        fake.fail_permanent_at = 1  # 第二张失败

        with pytest.raises(WeChatAPIError):
            draft_tools.create_newspic_draft("中途失败", paths)
        assert fake.drafts_created == [], "任一图片失败不得创建草稿"


class TestMaterialTools:
    def test_list_drafts_format(self, fake):
        result = material_tools.list_drafts()
        assert result["total"] == 2
        assert [i["media_id"] for i in result["items"]] == ["D1", "D2"]

    def test_get_draft(self, fake):
        assert material_tools.get_draft("D1")["news_item"][0]["title"] == "草稿一"

    def test_get_draft_empty_id_rejected(self, fake):
        with pytest.raises(ValueError, match="media_id"):
            material_tools.get_draft("  ")

    def test_delete_draft(self, fake):
        assert material_tools.delete_draft("D1") == {"media_id": "D1", "deleted": True}

    def test_delete_draft_empty_id_rejected(self, fake):
        with pytest.raises(ValueError, match="media_id"):
            material_tools.delete_draft("")
