"""tools/draft.py 与 tools/material.py：编排逻辑（monkeypatch core 客户端）。"""

from __future__ import annotations

import pytest

from wechat_mcp_publisher.config import Config
from wechat_mcp_publisher.core.exceptions import WeChatAPIError
from wechat_mcp_publisher.core.models import DraftPage, DraftSummary, MaterialImage
from wechat_mcp_publisher.tools import draft as draft_tools
from wechat_mcp_publisher.tools import material as material_tools

TINY_JPG = b"\xff\xd8\xff\xe0fakejpg"


class FakeClient:
    def __init__(self):
        self.config = Config(app_id="x", app_secret="y")  # 开关均 None=未设置
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

        result = draft_tools.create_newspic_draft("多图", "说明文字", paths)

        assert result["image_count"] == 3
        article = fake.drafts_created[0][0]
        assert article["article_type"] == "newspic"
        assert article["content"] == "说明文字"
        image_list = article["image_info"]["image_list"]
        assert [item["image_media_id"] for item in image_list] == ["PERM-1", "PERM-2", "PERM-3"]

    def test_zero_images_rejected_before_upload(self, fake):
        with pytest.raises(ValueError, match="1~20"):
            draft_tools.create_newspic_draft("无图", "说明", [])
        assert fake.permanent_uploads == [], "数量越界时不应上传任何图片"

    def test_too_many_images_rejected(self, fake):
        with pytest.raises(ValueError, match="1~20"):
            draft_tools.create_newspic_draft("超量", "说明", [f"/tmp/{i}.jpg" for i in range(21)])

    def test_upload_failure_no_draft_created(self, fake, tmp_path):
        paths = []
        for i in range(2):
            p = tmp_path / f"img{i}.jpg"
            p.write_bytes(TINY_JPG)
            paths.append(str(p))
        fake.fail_permanent_at = 1  # 第二张失败

        with pytest.raises(WeChatAPIError):
            draft_tools.create_newspic_draft("中途失败", "说明", paths)
        assert fake.drafts_created == [], "任一图片失败不得创建草稿"


class TestCommentFlags:
    """三层优先级：入参 > .env(Config) > 内置默认（need=1 / only_fans=0）。"""

    def _article(self, fake) -> dict:
        assert fake.drafts_created, "应已创建草稿"
        return fake.drafts_created[0][0]

    def test_builtin_defaults_on_news(self, fake, cover):
        draft_tools.create_news_draft("标题", "<p>x</p>", cover)
        article = self._article(fake)
        assert article["need_open_comment"] == 1
        assert article["only_fans_can_comment"] == 0
        assert isinstance(article["need_open_comment"], int)

    def test_env_overrides_builtin(self, fake, cover):
        fake.config = Config(app_id="x", app_secret="y", need_open_comment=False,
                             only_fans_can_comment=True)
        draft_tools.create_news_draft("标题", "<p>x</p>", cover)
        article = self._article(fake)
        assert article["need_open_comment"] == 0
        assert article["only_fans_can_comment"] == 1

    def test_param_overrides_env(self, fake, cover):
        fake.config = Config(app_id="x", app_secret="y", need_open_comment=True,
                             only_fans_can_comment=True)
        draft_tools.create_news_draft("标题", "<p>x</p>", cover,
                                      need_open_comment=False,
                                      only_fans_can_comment=False)
        article = self._article(fake)
        assert article["need_open_comment"] == 0
        assert article["only_fans_can_comment"] == 0

    def test_flags_on_newspic(self, fake, tmp_path):
        img = tmp_path / "i.jpg"
        img.write_bytes(TINY_JPG)
        # .env 层未设置 → 内置默认；入参显式关留言
        draft_tools.create_newspic_draft("标题", "说明", [str(img)],
                                         need_open_comment=False)
        article = self._article(fake)
        assert article["need_open_comment"] == 0
        assert article["only_fans_can_comment"] == 0

    def test_newspic_env_override(self, fake, tmp_path):
        img = tmp_path / "i.jpg"
        img.write_bytes(TINY_JPG)
        fake.config = Config(app_id="x", app_secret="y", only_fans_can_comment=True)
        draft_tools.create_newspic_draft("标题", "说明", [str(img)])
        article = self._article(fake)
        assert article["need_open_comment"] == 1, "未配置项走内置默认"
        assert article["only_fans_can_comment"] == 1, ".env 改写默认"


class TestNewsFieldValidation:
    """长度预校验：title ≤64 字、digest ≤120 字，超限零网络副作用。"""

    def _article(self, fake) -> dict:
        return fake.drafts_created[0][0]

    def test_title_over_64_rejected(self, fake, cover):
        with pytest.raises(ValueError, match="64"):
            draft_tools.create_news_draft("标" * 65, "<p>x</p>", cover)
        assert fake.drafts_created == [] and fake.permanent_uploads == []

    def test_digest_over_120_rejected(self, fake, cover):
        with pytest.raises(ValueError, match="120"):
            draft_tools.create_news_draft("标题", "<p>x</p>", cover, digest="摘" * 121)
        assert fake.drafts_created == [] and fake.permanent_uploads == []

    def test_boundary_64_120_passes(self, fake, cover):
        draft_tools.create_news_draft("标" * 64, "<p>x</p>", cover, digest="摘" * 120)
        article = self._article(fake)
        assert article["title"] == "标" * 64
        assert article["digest"] == "摘" * 120


class TestNewspicFieldValidation:
    """newspic 预校验：title ≤20 字；content 必填、≤1000 字、纯文本。"""

    def _no_side_effects(self, fake) -> None:
        assert fake.drafts_created == [] and fake.permanent_uploads == []

    def test_title_over_20_rejected(self, fake, tmp_path):
        img = tmp_path / "i.jpg"; img.write_bytes(TINY_JPG)
        with pytest.raises(ValueError, match="20"):
            draft_tools.create_newspic_draft("标" * 21, "说明", [str(img)])
        self._no_side_effects(fake)

    def test_empty_content_rejected(self, fake, tmp_path):
        img = tmp_path / "i.jpg"; img.write_bytes(TINY_JPG)
        with pytest.raises(ValueError, match="content 不能为空"):
            draft_tools.create_newspic_draft("标题", "   ", [str(img)])
        self._no_side_effects(fake)

    def test_content_over_1000_rejected(self, fake, tmp_path):
        img = tmp_path / "i.jpg"; img.write_bytes(TINY_JPG)
        with pytest.raises(ValueError, match="1000"):
            draft_tools.create_newspic_draft("标题", "文" * 1001, [str(img)])
        self._no_side_effects(fake)

    def test_html_tags_stripped_not_rejected(self, fake, tmp_path):
        img = tmp_path / "i.jpg"; img.write_bytes(TINY_JPG)
        result = draft_tools.create_newspic_draft(
            "标题", "<p>这不是<b>纯文本</b></p>", [str(img)]
        )
        cleaned = fake.drafts_created[0][0]["content"]
        assert cleaned == "这不是纯文本\n", "标签剥离、</p> 转换行"
        assert result["content"] == cleaned, "返回值带回实际使用的内容"

    def test_br_and_entities_cleaned(self, fake, tmp_path):
        img = tmp_path / "i.jpg"; img.write_bytes(TINY_JPG)
        draft_tools.create_newspic_draft("标题", "行一<br>行二 &amp; 更多", [str(img)])
        assert fake.drafts_created[0][0]["content"] == "行一\n行二 & 更多"

    def test_tags_only_content_counts_as_empty(self, fake, tmp_path):
        img = tmp_path / "i.jpg"; img.write_bytes(TINY_JPG)
        with pytest.raises(ValueError, match="content 不能为空"):
            draft_tools.create_newspic_draft("标题", "<br><p></p>", [str(img)])
        self._no_side_effects(fake)

    def test_length_checked_after_cleaning(self, fake, tmp_path):
        img = tmp_path / "i.jpg"; img.write_bytes(TINY_JPG)
        # 原文 130×8=1040 字符（超 1000 上限），剥离标签后 130 字 → 应通过
        raw = "<b>字</b>" * 130
        draft_tools.create_newspic_draft("标题", raw, [str(img)])
        assert len(fake.drafts_created[0][0]["content"]) == 130

    def test_plain_angle_bracket_not_flagged(self, fake, tmp_path):
        img = tmp_path / "i.jpg"; img.write_bytes(TINY_JPG)
        draft_tools.create_newspic_draft("标题", "3<5 是真话", [str(img)])
        assert fake.drafts_created, "非标签形态的 < 不应误伤"

    def test_boundary_20_1000_passes(self, fake, tmp_path):
        img = tmp_path / "i.jpg"; img.write_bytes(TINY_JPG)
        draft_tools.create_newspic_draft("标" * 20, "文" * 1000, [str(img)])
        article = fake.drafts_created[0][0]
        assert article["title"] == "标" * 20
        assert article["content"] == "文" * 1000


class TestAuthorResolution:
    """作者名三层：入参 > .env(WECHAT_AUTHOR) > 内置默认空串。"""

    def _article(self, fake) -> dict:
        return fake.drafts_created[0][0]

    def test_builtin_default_empty(self, fake, cover):
        draft_tools.create_news_draft("标题", "<p>x</p>", cover)
        assert self._article(fake)["author"] == ""

    def test_env_author(self, fake, cover):
        fake.config = Config(app_id="x", app_secret="y", author="公众号编辑")
        draft_tools.create_news_draft("标题", "<p>x</p>", cover)
        assert self._article(fake)["author"] == "公众号编辑"

    def test_param_overrides_env(self, fake, cover):
        fake.config = Config(app_id="x", app_secret="y", author="公众号编辑")
        draft_tools.create_news_draft("标题", "<p>x</p>", cover, author="特邀作者")
        assert self._article(fake)["author"] == "特邀作者"

    def test_explicit_empty_overrides_env(self, fake, cover):
        fake.config = Config(app_id="x", app_secret="y", author="公众号编辑")
        draft_tools.create_news_draft("标题", "<p>x</p>", cover, author="")
        assert self._article(fake)["author"] == ""


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
