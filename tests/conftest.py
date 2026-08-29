from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.core.auth import CurrentUser


USER_A = CurrentUser(
    id=UUID("11111111-1111-1111-1111-111111111111"),
    email="user-a@example.com",
    name="Seeded User A",
)
USER_B = CurrentUser(
    id=UUID("22222222-2222-2222-2222-222222222222"),
    email="user-b@example.com",
    name="Seeded User B",
)
AGENT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
SOURCE_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
NOW = datetime(2026, 8, 29, 20, 0, tzinfo=timezone.utc)


class Record(dict):
    def __getattr__(self, item):
        return self[item]


@dataclass
class FakeUploaded:
    id: str = "file_test"


class FakeOpenAI:
    def __init__(self) -> None:
        self.uploaded: list[tuple[str, bytes]] = []
        self.attached: list[tuple[str, str]] = []
        self.deleted_files: list[str] = []
        self.removed: list[tuple[str, str]] = []
        self.transcribed: list[str] = []
        self.described_images: list[str] = []

    async def upload_file(self, filename: str, data: bytes) -> FakeUploaded:
        self.uploaded.append((filename, data))
        return FakeUploaded()

    async def attach_file_to_vector_store(
        self,
        *,
        vector_store_id: str,
        file_id: str,
        source_type: str,
        title: str,
    ) -> None:
        self.attached.append((vector_store_id, file_id))

    async def remove_file_from_vector_store(self, *, vector_store_id: str, file_id: str) -> None:
        self.removed.append((vector_store_id, file_id))

    async def delete_file(self, file_id: str) -> None:
        self.deleted_files.append(file_id)

    async def transcribe_audio(self, filename: str, data: bytes) -> str:
        self.transcribed.append(filename)
        return "transcribed meeting notes"

    async def describe_image(self, filename: str, content_type: str, data: bytes) -> str:
        self.described_images.append(filename)
        return "image text and visual description"


class FakePool:
    def __init__(self, *, agent_owner=USER_A.id, source_exists=True, insert_raises=False) -> None:
        self.agent_owner = agent_owner
        self.source_exists = source_exists
        self.insert_raises = insert_raises
        self.inserted = False

    async def fetchrow(self, query: str, *args):
        if "SELECT openai_vector_store_id" in query:
            agent_id, user_id = args
            if agent_id == AGENT_ID and user_id == self.agent_owner:
                return Record(openai_vector_store_id="vs_test")
            return None

        if "INSERT INTO knowledge_sources" in query:
            if self.insert_raises:
                raise RuntimeError("insert failed")
            self.inserted = True
            source_id, agent_id, _user_id, source_type, title, filename, source_url, preview, file_id, byte_size = args
            return Record(
                id=source_id,
                agent_id=agent_id,
                source_type=source_type,
                status="ready",
                title=title,
                original_filename=filename,
                source_url=source_url,
                content_preview=preview,
                openai_file_id=file_id,
                byte_size=byte_size,
                error_message=None,
                created_at=NOW,
            )

        if "FROM knowledge_sources ks" in query:
            if not self.source_exists:
                return None
            return Record(
                id=SOURCE_ID,
                agent_id=AGENT_ID,
                source_type="markdown",
                status="ready",
                title="source.md",
                original_filename="source.md",
                source_url=None,
                content_preview="hello",
                openai_file_id="file_test",
                byte_size=5,
                error_message=None,
                created_at=NOW,
            )

        return None

    async def fetch(self, query: str, *args):
        return []


@pytest.fixture
def fake_openai() -> FakeOpenAI:
    return FakeOpenAI()
