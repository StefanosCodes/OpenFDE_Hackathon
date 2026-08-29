import pytest

from app.schemas.agents import AgentDesignPreviewRequest
from app.services.agents import preview_agent_design_from_draft


@pytest.mark.asyncio
async def test_draft_design_preview_includes_tool_graph():
    preview = await preview_agent_design_from_draft(
        body=AgentDesignPreviewRequest(
            name="Due Diligence Agent",
            goal="Answer diligence questions from uploaded data room files.",
            source_types=["pdf", "excel", "audio", "video", "image", "pdf"],
            enabled_tools=["file_search"],
        )
    )

    assert preview.agent_name == "Due Diligence Agent"
    assert preview.source_counts == {"pdf": 0, "excel": 0, "audio": 0, "video": 0, "image": 0}
    assert "FileSearchTool" in preview.mermaid
    assert "video audio track" in preview.mermaid
    assert "OpenAI Vector Store" in preview.mermaid
    assert any(tool.name == "audio_transcription" for tool in preview.tools)
    assert any(tool.name == "video_transcription" for tool in preview.tools)
    assert any(tool.name == "image_understanding" for tool in preview.tools)
