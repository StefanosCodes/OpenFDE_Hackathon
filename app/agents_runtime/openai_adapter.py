import base64
import io
from dataclasses import dataclass

from openai import AsyncOpenAI

from app.core.settings import settings


@dataclass(frozen=True)
class UploadedFile:
    id: str


@dataclass(frozen=True)
class VectorStore:
    id: str


class OpenAIAdapter:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def create_vector_store(self, name: str) -> VectorStore:
        store = await self._client.vector_stores.create(name=name)
        return VectorStore(id=store.id)

    async def delete_vector_store(self, vector_store_id: str) -> None:
        await self._client.vector_stores.delete(vector_store_id=vector_store_id)

    async def upload_file(self, filename: str, data: bytes) -> UploadedFile:
        file_obj = io.BytesIO(data)
        file_obj.name = filename
        uploaded = await self._client.files.create(file=file_obj, purpose="assistants")
        return UploadedFile(id=uploaded.id)

    async def transcribe_audio(self, filename: str, data: bytes) -> str:
        file_obj = io.BytesIO(data)
        file_obj.name = filename
        transcript = await self._client.audio.transcriptions.create(
            model=settings.openai_transcription_model,
            file=file_obj,
        )
        return str(transcript.text)

    async def describe_image(self, filename: str, content_type: str, data: bytes) -> str:
        encoded = base64.b64encode(data).decode("ascii")
        response = await self._client.responses.create(
            model=settings.openai_model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Extract readable text from this image and summarize the visual content. "
                                "Return concise notes suitable for a knowledge base."
                            ),
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:{content_type};base64,{encoded}",
                        },
                    ],
                }
            ],
        )
        return str(response.output_text)

    async def attach_file_to_vector_store(
        self,
        *,
        vector_store_id: str,
        file_id: str,
        source_type: str,
        title: str,
    ) -> None:
        await self._client.vector_stores.files.create(
            vector_store_id=vector_store_id,
            file_id=file_id,
            attributes={"source_type": source_type, "title": title[:512]},
        )

    async def remove_file_from_vector_store(self, *, vector_store_id: str, file_id: str) -> None:
        await self._client.vector_stores.files.delete(
            vector_store_id=vector_store_id,
            file_id=file_id,
        )

    async def delete_file(self, file_id: str) -> None:
        await self._client.files.delete(file_id)


def get_openai_adapter() -> OpenAIAdapter:
    return OpenAIAdapter()
