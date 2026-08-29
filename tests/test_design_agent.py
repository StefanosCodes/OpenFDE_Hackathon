import json
from types import SimpleNamespace

import pytest

from app.schemas.design import (
    DesignArtifactRequest,
    DesignChatMessage,
    DesignChatRequest,
)
from app.services import design_agent


@pytest.mark.anyio
async def test_design_chat_falls_back_to_guided_interview(monkeypatch):
    monkeypatch.setattr(
        design_agent,
        "settings",
        SimpleNamespace(openai_api_key=None, openai_model="gpt-4.1-mini"),
    )

    response = await design_agent.design_chat(
        DesignChatRequest(
            messages=[
                DesignChatMessage(
                    role="user",
                    content="Build an onboarding agent for enterprise customers",
                )
            ],
            enabled_connector_ids=["google-drive"],
        )
    )

    assert response.assistant_message
    assert response.suggested_agent_name.startswith("Build an onboarding")
    assert response.readiness_score > 0
    assert response.can_generate_design is False


@pytest.mark.anyio
async def test_design_artifact_returns_canvas_and_dataset(monkeypatch):
    monkeypatch.setattr(
        design_agent,
        "settings",
        SimpleNamespace(openai_api_key=None, openai_model="gpt-4.1-mini"),
    )

    response = await design_agent.design_artifact(
        DesignArtifactRequest(
            agent_name="Customer Onboarding Agent",
            messages=[
                DesignChatMessage(
                    role="user",
                    content="Help CSMs onboard new customers using uploaded playbooks.",
                ),
                DesignChatMessage(
                    role="assistant",
                    content="What usually starts the onboarding workflow?",
                ),
                DesignChatMessage(
                    role="user",
                    content="A signed contract in Salesforce and an implementation kickoff.",
                ),
            ],
            enabled_connector_ids=["google-drive", "slack"],
        )
    )

    assert response.markdown.startswith("# Customer Onboarding Agent")
    assert len(response.canvas.nodes) >= 4
    assert len(response.canvas.edges) >= 3
    assert "flowchart TD" in response.mermaid
    assert response.knowledge_sources
    assert response.intents
    assert response.datasets
    assert response.datasets[0].grading["type"] == "rubric"
    source_row = json.loads(response.dataset_exports.eval_source_jsonl.splitlines()[0])
    promptfoo_row = json.loads(response.dataset_exports.promptfoo_jsonl.splitlines()[0])
    deepeval_row = json.loads(response.dataset_exports.deepeval_jsonl.splitlines()[0])

    assert source_row["reference_context"]
    assert promptfoo_row["vars"]["input"] == source_row["input"]
    assert promptfoo_row["assert"][0]["type"] == "llm-rubric"
    assert deepeval_row["context"] == source_row["reference_context"]
    assert deepeval_row["additional_metadata"]["id"] == source_row["id"]


@pytest.mark.anyio
async def test_design_artifact_normalizes_overlapping_canvas_nodes(monkeypatch):
    async def fake_model(**kwargs):
        return {
            "agent_name": "Crowded Map",
            "markdown": "# Crowded Map",
            "nodes": [
                {
                    "id": "a",
                    "kind": "start",
                    "label": "Very long user initiation node label",
                    "description": "A very long description that would make the visual map hard to scan.",
                    "x": 0,
                    "y": 0,
                },
                {
                    "id": "b",
                    "kind": "message",
                    "label": "Very long discovery workflow label",
                    "description": "Another long description that should be shortened by the backend.",
                    "x": 5,
                    "y": 0,
                },
                {
                    "id": "c",
                    "kind": "knowledge",
                    "label": "RAG lookup",
                    "description": "Search scoped knowledge",
                    "x": 10,
                    "y": 0,
                },
            ],
            "edges": [
                {"id": "a-b", "source": "a", "target": "b"},
                {"id": "b-c", "source": "b", "target": "c"},
            ],
            "knowledge_sources": [
                {
                    "id": "knowledge-001",
                    "title": "Playbook",
                    "source_type": "file",
                    "description": "Uploaded workflow playbook",
                    "required": True,
                    "metadata": {"scope": "agent"},
                }
            ],
            "intents": [
                {
                    "id": "intent-001",
                    "name": "Answer workflow question",
                    "trigger": "User asks about the process.",
                    "expected_outcome": "Agent answers from knowledge.",
                    "required_tools": ["file_search"],
                    "success_criteria": ["Answer is grounded."],
                    "metadata": {"priority": "high"},
                }
            ],
            "datasets": [
                {
                    "id": "case-001",
                    "input": "Question",
                    "expected_output": "Answer",
                    "reference_context": ["Context"],
                    "grading": {"type": "rubric", "rubric": "Grounded answer"},
                    "expected_tools": ["file_search"],
                    "metadata": {"category": "happy_path"},
                }
            ],
        }

    monkeypatch.setattr(design_agent, "_call_json_model", fake_model)

    response = await design_agent.design_artifact(
        DesignArtifactRequest(
            agent_name="Crowded Map",
            messages=[
                DesignChatMessage(role="user", content="Build an agent map.")
            ],
            enabled_connector_ids=[],
        )
    )

    positions = [node.position for node in response.canvas.nodes]
    assert [position.x for position in positions] == sorted(position.x for position in positions)
    assert positions[1].x - positions[0].x >= 300
    assert positions[2].x - positions[1].x >= 300
    assert len(response.canvas.nodes[0].data.label) <= 36
    assert len(response.canvas.nodes[0].data.description) <= 72


@pytest.mark.anyio
async def test_design_artifact_creates_sequential_edges_when_model_omits_edges(monkeypatch):
    async def fake_model(**kwargs):
        return {
            "agent_name": "No Edge Map",
            "markdown": "# No Edge Map",
            "nodes": [
                {"id": "start", "kind": "start", "label": "Start", "description": "Begin"},
                {"id": "rag", "kind": "knowledge", "label": "RAG", "description": "Search"},
                {"id": "finish", "kind": "finish", "label": "Finish", "description": "Answer"},
            ],
            "edges": [],
            "knowledge_sources": [
                {
                    "id": "knowledge-001",
                    "title": "Knowledge base",
                    "source_type": "file",
                    "description": "Uploaded files",
                    "required": True,
                    "metadata": {},
                }
            ],
            "intents": [
                {
                    "id": "intent-001",
                    "name": "Answer",
                    "trigger": "User asks",
                    "expected_outcome": "Agent answers",
                    "required_tools": ["file_search"],
                    "success_criteria": ["Grounded"],
                    "metadata": {},
                }
            ],
            "datasets": [
                {
                    "id": "case-001",
                    "input": "Question",
                    "expected_output": "Answer",
                    "reference_context": ["Context"],
                    "grading": {"type": "rubric", "rubric": "Grounded answer"},
                    "expected_tools": ["file_search"],
                    "metadata": {"category": "happy_path"},
                }
            ],
        }

    monkeypatch.setattr(design_agent, "_call_json_model", fake_model)

    response = await design_agent.design_artifact(
        DesignArtifactRequest(
            agent_name="No Edge Map",
            messages=[DesignChatMessage(role="user", content="Build an agent.")],
            enabled_connector_ids=[],
        )
    )

    assert [(edge.source, edge.target) for edge in response.canvas.edges] == [
        ("start", "rag"),
        ("rag", "finish"),
    ]
    assert response.knowledge_sources[0].title == "Knowledge base"
    assert response.intents[0].required_tools == ["file_search"]
