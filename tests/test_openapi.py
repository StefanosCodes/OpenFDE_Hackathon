from app.main import app


def test_openapi_contains_knowledge_endpoints():
    schema = app.openapi()
    paths = schema["paths"]

    assert "/v1/agents/design-preview" in paths
    assert "/v1/agents/{agent_id}/design-preview" in paths
    assert "/v1/agents/{agent_id}/knowledge-sources/markdown" in paths
    assert "/v1/agents/{agent_id}/knowledge-sources/pdf" in paths
    assert "/v1/agents/{agent_id}/knowledge-sources/files" in paths
    assert "/v1/agents/{agent_id}/knowledge-sources/url" in paths
    assert "/v1/agents/{agent_id}/knowledge-sources" in paths
    assert "/v1/agents/{agent_id}/knowledge-sources/{source_id}" in paths
    assert "/v1/connectors/github/connect" in paths
    assert "/v1/connectors/github" in paths
    assert "/v1/connectors/github/repositories" in paths
    assert "/v1/connectors/github/repository" in paths
    assert "/v1/integrations/github/webhook" in paths
    assert "/v1/agent-design/chat" in paths
    assert "/v1/agent-design/artifact" in paths
