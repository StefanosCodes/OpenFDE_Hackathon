from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg
from fastapi import UploadFile

from app.agents_runtime.openai_adapter import OpenAIAdapter
from app.core.auth import CurrentUser
from app.core.database import get_pool, transaction
from app.core.http import not_found, unprocessable
from app.schemas.knowledge import KnowledgeSourceResponse
from app.services.file_preview import csv_preview, docx_preview, pptx_preview, xlsx_preview
from app.services.url_fetch import MAX_URL_BYTES, fetch_url_source


MAX_MARKDOWN_BYTES = 2 * 1024 * 1024
MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_TEXT_BYTES = 2 * 1024 * 1024
MAX_CSV_BYTES = 5 * 1024 * 1024
MAX_OFFICE_BYTES = 20 * 1024 * 1024
MAX_AUDIO_BYTES = 25 * 1024 * 1024
MAX_IMAGE_BYTES = 10 * 1024 * 1024
PREVIEW_CHARS = 4000
MARKDOWN_CONTENT_TYPES = {"text/markdown", "text/plain"}
PDF_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
TEXT_CONTENT_TYPES = {"text/plain"}
CSV_CONTENT_TYPES = {"text/csv", "application/csv", "application/vnd.ms-excel"}
WORD_CONTENT_TYPES = {
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
EXCEL_CONTENT_TYPES = {
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
POWERPOINT_CONTENT_TYPES = {
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
AUDIO_CONTENT_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "video/mp4",
}
IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}


@dataclass(frozen=True)
class FileKind:
    source_type: str
    max_bytes: int
    extensions: set[str]
    content_types: set[str]


FILE_KINDS = {
    "markdown": FileKind("markdown", MAX_MARKDOWN_BYTES, {".md", ".markdown"}, MARKDOWN_CONTENT_TYPES),
    "pdf": FileKind("pdf", MAX_PDF_BYTES, {".pdf"}, PDF_CONTENT_TYPES),
    "text": FileKind("text", MAX_TEXT_BYTES, {".txt", ".log"}, TEXT_CONTENT_TYPES),
    "csv": FileKind("csv", MAX_CSV_BYTES, {".csv", ".tsv"}, CSV_CONTENT_TYPES),
    "word": FileKind("word", MAX_OFFICE_BYTES, {".doc", ".docx"}, WORD_CONTENT_TYPES),
    "excel": FileKind("excel", MAX_OFFICE_BYTES, {".xls", ".xlsx"}, EXCEL_CONTENT_TYPES),
    "powerpoint": FileKind("powerpoint", MAX_OFFICE_BYTES, {".ppt", ".pptx"}, POWERPOINT_CONTENT_TYPES),
    "audio": FileKind("audio", MAX_AUDIO_BYTES, {".mp3", ".m4a", ".wav", ".webm", ".mp4"}, AUDIO_CONTENT_TYPES),
    "image": FileKind("image", MAX_IMAGE_BYTES, {".png", ".jpg", ".jpeg", ".webp", ".gif"}, IMAGE_CONTENT_TYPES),
}


def _source_from_record(row: asyncpg.Record) -> KnowledgeSourceResponse:
    return KnowledgeSourceResponse(
        id=row["id"],
        agent_id=row["agent_id"],
        source_type=row["source_type"],
        status=row["status"],
        title=row["title"],
        original_filename=row["original_filename"],
        source_url=row["source_url"],
        content_preview=row["content_preview"],
        openai_file_id=row["openai_file_id"],
        byte_size=row["byte_size"],
        error_message=row["error_message"],
        created_at=row["created_at"],
    )


async def _get_owned_agent_vector_store(*, user: CurrentUser, agent_id: UUID) -> str:
    row = await get_pool().fetchrow(
        """
        SELECT openai_vector_store_id
        FROM agents
        WHERE id = $1
          AND owner_user_id = $2
        """,
        agent_id,
        user.id,
    )
    if row is None:
        raise not_found()
    return row["openai_vector_store_id"]


async def create_markdown_source(
    *,
    user: CurrentUser,
    agent_id: UUID,
    file: UploadFile,
    title: str | None,
    openai: OpenAIAdapter,
) -> KnowledgeSourceResponse:
    vector_store_id = await _get_owned_agent_vector_store(user=user, agent_id=agent_id)
    data = await _read_upload(file, MAX_MARKDOWN_BYTES)
    filename = file.filename or "source.md"
    if Path(filename).suffix.lower() != ".md" and file.content_type not in MARKDOWN_CONTENT_TYPES:
        raise unprocessable("Markdown source must be .md, text/markdown, or text/plain")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise unprocessable("Markdown source must be valid UTF-8") from exc

    return await _upload_and_insert_source(
        user=user,
        agent_id=agent_id,
        vector_store_id=vector_store_id,
        source_type="markdown",
        title=_clean_title(title or filename),
        filename=filename,
        source_url=None,
        data=data,
        content_preview=text[:PREVIEW_CHARS],
        openai=openai,
    )


async def create_pdf_source(
    *,
    user: CurrentUser,
    agent_id: UUID,
    file: UploadFile,
    title: str | None,
    openai: OpenAIAdapter,
) -> KnowledgeSourceResponse:
    vector_store_id = await _get_owned_agent_vector_store(user=user, agent_id=agent_id)
    data = await _read_upload(file, MAX_PDF_BYTES)
    filename = file.filename or "source.pdf"
    if file.content_type not in PDF_CONTENT_TYPES or not data.startswith(b"%PDF"):
        raise unprocessable("PDF source must be application/pdf content")

    return await _upload_and_insert_source(
        user=user,
        agent_id=agent_id,
        vector_store_id=vector_store_id,
        source_type="pdf",
        title=_clean_title(title or filename),
        filename=filename,
        source_url=None,
        data=data,
        content_preview=None,
        openai=openai,
    )


async def create_url_source(
    *,
    user: CurrentUser,
    agent_id: UUID,
    url: str,
    title: str | None,
    openai: OpenAIAdapter,
) -> KnowledgeSourceResponse:
    vector_store_id = await _get_owned_agent_vector_store(user=user, agent_id=agent_id)
    data, content_type, final_url = await fetch_url_source(url)
    if len(data) > MAX_URL_BYTES:
        raise unprocessable("URL response is too large")

    if content_type == "application/pdf":
        if not data.startswith(b"%PDF"):
            raise unprocessable("URL PDF content is invalid")
        source_type = "url"
        filename = "source.pdf"
        preview = None
    else:
        source_type = "url"
        filename = "source.txt"
        preview = data.decode("utf-8", errors="replace")[:PREVIEW_CHARS]

    return await _upload_and_insert_source(
        user=user,
        agent_id=agent_id,
        vector_store_id=vector_store_id,
        source_type=source_type,
        title=_clean_title(title or url),
        filename=filename,
        source_url=url,
        data=data,
        content_preview=preview,
        openai=openai,
    )


async def create_file_source(
    *,
    user: CurrentUser,
    agent_id: UUID,
    file: UploadFile,
    title: str | None,
    openai: OpenAIAdapter,
) -> KnowledgeSourceResponse:
    vector_store_id = await _get_owned_agent_vector_store(user=user, agent_id=agent_id)
    filename = file.filename or "source"
    kind = _classify_file(filename=filename, content_type=file.content_type)
    data = await _read_upload(file, kind.max_bytes)
    suffix = Path(filename).suffix.lower()
    content_type = _base_content_type(file.content_type)

    if kind.source_type == "pdf":
        if not data.startswith(b"%PDF"):
            raise unprocessable("PDF source must be application/pdf content")
        upload_filename = filename
        upload_data = data
        preview = None
    elif kind.source_type == "markdown":
        preview = _require_utf8(data, "Markdown source")[:PREVIEW_CHARS]
        upload_filename = filename
        upload_data = data
    elif kind.source_type == "text":
        preview = _require_utf8(data, "Text source")[:PREVIEW_CHARS]
        upload_filename = filename
        upload_data = data
    elif kind.source_type == "csv":
        preview = csv_preview(data, PREVIEW_CHARS)
        upload_filename = filename
        upload_data = data
    elif kind.source_type == "word":
        preview = docx_preview(data, PREVIEW_CHARS) if suffix == ".docx" else None
        upload_filename = filename
        upload_data = data
    elif kind.source_type == "excel":
        preview = xlsx_preview(data, PREVIEW_CHARS) if suffix == ".xlsx" else None
        upload_filename = filename
        upload_data = data
    elif kind.source_type == "powerpoint":
        preview = pptx_preview(data, PREVIEW_CHARS) if suffix == ".pptx" else None
        upload_filename = filename
        upload_data = data
    elif kind.source_type == "audio":
        transcript = await openai.transcribe_audio(filename=filename, data=data)
        preview = transcript[:PREVIEW_CHARS]
        upload_filename = f"{Path(filename).stem or 'audio'}-transcript.txt"
        upload_data = transcript.encode("utf-8")
    elif kind.source_type == "image":
        description = await openai.describe_image(filename=filename, content_type=content_type, data=data)
        preview = description[:PREVIEW_CHARS]
        upload_filename = f"{Path(filename).stem or 'image'}-description.txt"
        upload_data = description.encode("utf-8")
    else:
        raise unprocessable("Unsupported file type")

    return await _upload_and_insert_source(
        user=user,
        agent_id=agent_id,
        vector_store_id=vector_store_id,
        source_type=kind.source_type,
        title=_clean_title(title or filename),
        filename=filename,
        source_url=None,
        data=upload_data,
        content_preview=preview,
        openai=openai,
        upload_filename=upload_filename,
        original_byte_size=len(data),
    )


async def list_sources(
    *,
    user: CurrentUser,
    agent_id: UUID,
    limit: int,
) -> list[KnowledgeSourceResponse]:
    await _get_owned_agent_vector_store(user=user, agent_id=agent_id)
    rows = await get_pool().fetch(
        """
        SELECT ks.id, ks.agent_id, ks.source_type, ks.status, ks.title,
               ks.original_filename, ks.source_url, ks.content_preview,
               ks.openai_file_id, ks.byte_size, ks.error_message, ks.created_at
        FROM knowledge_sources ks
        JOIN agents a ON a.id = ks.agent_id
        WHERE ks.agent_id = $1
          AND a.owner_user_id = $2
        ORDER BY ks.created_at DESC, ks.id DESC
        LIMIT $3
        """,
        agent_id,
        user.id,
        limit,
    )
    return [_source_from_record(row) for row in rows]


async def get_source(
    *,
    user: CurrentUser,
    agent_id: UUID,
    source_id: UUID,
) -> KnowledgeSourceResponse:
    row = await get_pool().fetchrow(
        """
        SELECT ks.id, ks.agent_id, ks.source_type, ks.status, ks.title,
               ks.original_filename, ks.source_url, ks.content_preview,
               ks.openai_file_id, ks.byte_size, ks.error_message, ks.created_at
        FROM knowledge_sources ks
        JOIN agents a ON a.id = ks.agent_id
        WHERE ks.id = $1
          AND ks.agent_id = $2
          AND a.owner_user_id = $3
        """,
        source_id,
        agent_id,
        user.id,
    )
    if row is None:
        raise not_found()
    return _source_from_record(row)


async def delete_source(
    *,
    user: CurrentUser,
    agent_id: UUID,
    source_id: UUID,
    openai: OpenAIAdapter,
) -> None:
    vector_store_id = await _get_owned_agent_vector_store(user=user, agent_id=agent_id)
    source = await get_source(user=user, agent_id=agent_id, source_id=source_id)
    if source.openai_file_id:
        await openai.remove_file_from_vector_store(
            vector_store_id=vector_store_id,
            file_id=source.openai_file_id,
        )
        await openai.delete_file(source.openai_file_id)
    async with transaction() as conn:
        deleted = await conn.execute(
            """
            DELETE FROM knowledge_sources
            WHERE id = $1
              AND agent_id = $2
            """,
            source_id,
            agent_id,
        )
    if deleted == "DELETE 0":
        raise not_found()


async def _upload_and_insert_source(
    *,
    user: CurrentUser,
    agent_id: UUID,
    vector_store_id: str,
    source_type: str,
    title: str,
    filename: str,
    source_url: str | None,
    data: bytes,
    content_preview: str | None,
    openai: OpenAIAdapter,
    upload_filename: str | None = None,
    original_byte_size: int | None = None,
) -> KnowledgeSourceResponse:
    uploaded = await openai.upload_file(filename=upload_filename or filename, data=data)
    attached = False
    try:
        await openai.attach_file_to_vector_store(
            vector_store_id=vector_store_id,
            file_id=uploaded.id,
            source_type=source_type,
            title=title,
        )
        attached = True
        row = await get_pool().fetchrow(
            """
            INSERT INTO knowledge_sources (
                id, agent_id, created_by_user_id, source_type, status, title,
                original_filename, source_url, content_preview, openai_file_id,
                byte_size, error_message
            )
            VALUES ($1, $2, $3, $4, 'ready', $5, $6, $7, $8, $9, $10, NULL)
            RETURNING id, agent_id, source_type, status, title, original_filename,
                      source_url, content_preview, openai_file_id, byte_size,
                      error_message, created_at
            """,
            uuid4(),
            agent_id,
            user.id,
            source_type,
            title,
            filename,
            source_url,
            content_preview,
            uploaded.id,
            original_byte_size if original_byte_size is not None else len(data),
        )
    except Exception:
        if attached:
            await openai.remove_file_from_vector_store(
                vector_store_id=vector_store_id,
                file_id=uploaded.id,
            )
        await openai.delete_file(uploaded.id)
        raise
    return _source_from_record(row)


async def _read_upload(file: UploadFile, max_bytes: int) -> bytes:
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise unprocessable("Uploaded file is too large")
    if not data:
        raise unprocessable("Uploaded file is empty")
    return data


def _clean_title(title: str) -> str:
    cleaned = " ".join(title.strip().split())
    if not cleaned:
        raise unprocessable("Title cannot be empty")
    return cleaned[:500]


def _classify_file(*, filename: str, content_type: str | None) -> FileKind:
    suffix = Path(filename).suffix.lower()
    base_content_type = _base_content_type(content_type)
    for kind in FILE_KINDS.values():
        if suffix in kind.extensions or base_content_type in kind.content_types:
            return kind
    raise unprocessable("Unsupported file type")


def _base_content_type(content_type: str | None) -> str:
    if not content_type:
        return "application/octet-stream"
    return content_type.split(";", 1)[0].strip().lower()


def _require_utf8(data: bytes, label: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise unprocessable(f"{label} must be valid UTF-8") from exc
