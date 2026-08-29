import io
from contextlib import asynccontextmanager

import pytest
from fastapi import HTTPException

from app.services import knowledge
from tests.conftest import AGENT_ID, USER_A, USER_B, FakePool


class DummyUpload:
    def __init__(self, filename: str, content_type: str, data: bytes) -> None:
        self.filename = filename
        self.content_type = content_type
        self._file = io.BytesIO(data)

    async def read(self, size: int = -1) -> bytes:
        return self._file.read(size)


def upload_file(filename: str, content_type: str, data: bytes) -> DummyUpload:
    return DummyUpload(filename, content_type, data)


@pytest.mark.asyncio
async def test_markdown_ingest_happy_path(monkeypatch, fake_openai):
    pool = FakePool()
    monkeypatch.setattr(knowledge, "get_pool", lambda: pool)

    source = await knowledge.create_markdown_source(
        user=USER_A,
        agent_id=AGENT_ID,
        file=upload_file("notes.md", "text/markdown", b"# Secret\nunique-ray-phrase"),
        title=None,
        openai=fake_openai,
    )

    assert source.source_type == "markdown"
    assert source.title == "notes.md"
    assert source.content_preview.startswith("# Secret")
    assert source.openai_file_id == "file_test"
    assert pool.inserted is True
    assert fake_openai.attached == [("vs_test", "file_test")]


@pytest.mark.asyncio
async def test_other_user_agent_is_404(monkeypatch, fake_openai):
    pool = FakePool(agent_owner=USER_A.id)
    monkeypatch.setattr(knowledge, "get_pool", lambda: pool)

    with pytest.raises(HTTPException) as exc:
        await knowledge.create_markdown_source(
            user=USER_B,
            agent_id=AGENT_ID,
            file=upload_file("notes.md", "text/markdown", b"hello"),
            title=None,
            openai=fake_openai,
        )

    assert exc.value.status_code == 404
    assert pool.inserted is False


@pytest.mark.asyncio
async def test_bad_markdown_type_returns_422_without_upload(monkeypatch, fake_openai):
    pool = FakePool()
    monkeypatch.setattr(knowledge, "get_pool", lambda: pool)

    with pytest.raises(HTTPException) as exc:
        await knowledge.create_markdown_source(
            user=USER_A,
            agent_id=AGENT_ID,
            file=upload_file("run.exe", "application/octet-stream", b"MZ"),
            title=None,
            openai=fake_openai,
        )

    assert exc.value.status_code == 422
    assert fake_openai.uploaded == []
    assert pool.inserted is False


@pytest.mark.asyncio
async def test_pdf_requires_pdf_bytes(monkeypatch, fake_openai):
    pool = FakePool()
    monkeypatch.setattr(knowledge, "get_pool", lambda: pool)

    with pytest.raises(HTTPException) as exc:
        await knowledge.create_pdf_source(
            user=USER_A,
            agent_id=AGENT_ID,
            file=upload_file("fake.pdf", "application/pdf", b"not a pdf"),
            title=None,
            openai=fake_openai,
        )

    assert exc.value.status_code == 422
    assert fake_openai.uploaded == []
    assert pool.inserted is False


@pytest.mark.asyncio
async def test_cleanup_openai_file_when_db_insert_fails(monkeypatch, fake_openai):
    pool = FakePool(insert_raises=True)
    monkeypatch.setattr(knowledge, "get_pool", lambda: pool)

    with pytest.raises(RuntimeError):
        await knowledge.create_markdown_source(
            user=USER_A,
            agent_id=AGENT_ID,
            file=upload_file("notes.md", "text/markdown", b"hello"),
            title=None,
            openai=fake_openai,
        )

    assert fake_openai.removed == [("vs_test", "file_test")]
    assert fake_openai.deleted_files == ["file_test"]


@pytest.mark.asyncio
async def test_delete_source_removes_openai_file_then_row(monkeypatch, fake_openai):
    pool = FakePool()
    monkeypatch.setattr(knowledge, "get_pool", lambda: pool)

    class FakeConn:
        async def execute(self, query: str, *args):
            return "DELETE 1"

    @asynccontextmanager
    async def fake_transaction():
        yield FakeConn()

    monkeypatch.setattr(knowledge, "transaction", fake_transaction)

    from tests.conftest import SOURCE_ID

    await knowledge.delete_source(
        user=USER_A,
        agent_id=AGENT_ID,
        source_id=SOURCE_ID,
        openai=fake_openai,
    )

    assert fake_openai.removed == [("vs_test", "file_test")]
    assert fake_openai.deleted_files == ["file_test"]


@pytest.mark.asyncio
async def test_generic_csv_file_ingest(monkeypatch, fake_openai):
    pool = FakePool()
    monkeypatch.setattr(knowledge, "get_pool", lambda: pool)

    source = await knowledge.create_file_source(
        user=USER_A,
        agent_id=AGENT_ID,
        file=upload_file("accounts.csv", "text/csv", b"name,total\nRay,42\n"),
        title=None,
        openai=fake_openai,
    )

    assert source.source_type == "csv"
    assert "Ray | 42" in source.content_preview
    assert fake_openai.uploaded[0][0] == "accounts.csv"


@pytest.mark.asyncio
async def test_generic_audio_file_transcribes_then_uploads_text(monkeypatch, fake_openai):
    pool = FakePool()
    monkeypatch.setattr(knowledge, "get_pool", lambda: pool)

    source = await knowledge.create_file_source(
        user=USER_A,
        agent_id=AGENT_ID,
        file=upload_file("meeting.mp3", "audio/mpeg", b"audio bytes"),
        title=None,
        openai=fake_openai,
    )

    assert source.source_type == "audio"
    assert source.byte_size == len(b"audio bytes")
    assert source.content_preview == "transcribed meeting notes"
    assert fake_openai.transcribed == ["meeting.mp3"]
    assert fake_openai.uploaded[0] == ("meeting-transcript.txt", b"transcribed meeting notes")


@pytest.mark.asyncio
async def test_generic_image_file_describes_then_uploads_text(monkeypatch, fake_openai):
    pool = FakePool()
    monkeypatch.setattr(knowledge, "get_pool", lambda: pool)

    source = await knowledge.create_file_source(
        user=USER_A,
        agent_id=AGENT_ID,
        file=upload_file("whiteboard.png", "image/png", b"image bytes"),
        title=None,
        openai=fake_openai,
    )

    assert source.source_type == "image"
    assert source.content_preview == "image text and visual description"
    assert fake_openai.described_images == ["whiteboard.png"]
    assert fake_openai.uploaded[0] == ("whiteboard-description.txt", b"image text and visual description")


@pytest.mark.asyncio
async def test_generic_video_file_transcribes_then_uploads_text(monkeypatch, fake_openai):
    pool = FakePool()
    monkeypatch.setattr(knowledge, "get_pool", lambda: pool)

    source = await knowledge.create_file_source(
        user=USER_A,
        agent_id=AGENT_ID,
        file=upload_file("walkthrough.mp4", "video/mp4", b"video bytes"),
        title=None,
        openai=fake_openai,
    )

    assert source.source_type == "video"
    assert source.byte_size == len(b"video bytes")
    assert source.content_preview == "transcribed meeting notes"
    assert fake_openai.transcribed == ["walkthrough.mp4"]
    assert fake_openai.uploaded[0] == ("walkthrough-video-transcript.txt", b"transcribed meeting notes")


@pytest.mark.asyncio
async def test_generic_json_file_ingest(monkeypatch, fake_openai):
    pool = FakePool()
    monkeypatch.setattr(knowledge, "get_pool", lambda: pool)

    source = await knowledge.create_file_source(
        user=USER_A,
        agent_id=AGENT_ID,
        file=upload_file("config.json", "application/json", b'{"agent":"ray"}'),
        title=None,
        openai=fake_openai,
    )

    assert source.source_type == "json"
    assert "ray" in source.content_preview


@pytest.mark.asyncio
async def test_generic_html_file_uploads_visible_text(monkeypatch, fake_openai):
    pool = FakePool()
    monkeypatch.setattr(knowledge, "get_pool", lambda: pool)

    source = await knowledge.create_file_source(
        user=USER_A,
        agent_id=AGENT_ID,
        file=upload_file("page.html", "text/html", b"<html><script>bad()</script><body>Hello FDE</body></html>"),
        title=None,
        openai=fake_openai,
    )

    assert source.source_type == "html"
    assert source.content_preview == "Hello FDE"
    assert fake_openai.uploaded[0] == ("page-visible-text.txt", b"Hello FDE")
