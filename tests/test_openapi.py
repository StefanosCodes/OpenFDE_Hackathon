from app.main import app


def test_openapi_contains_knowledge_endpoints():
    schema = app.openapi()
    paths = schema["paths"]

    assert "/v1/agents/{agent_id}/knowledge-sources/markdown" in paths
    assert "/v1/agents/{agent_id}/knowledge-sources/pdf" in paths
    assert "/v1/agents/{agent_id}/knowledge-sources/files" in paths
    assert "/v1/agents/{agent_id}/knowledge-sources/url" in paths
    assert "/v1/agents/{agent_id}/knowledge-sources" in paths
    assert "/v1/agents/{agent_id}/knowledge-sources/{source_id}" in paths
