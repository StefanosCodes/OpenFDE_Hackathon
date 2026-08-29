from agents import Agent, FileSearchTool, Runner

from app.core.settings import settings


async def run_agent_with_file_search(
    *,
    agent_name: str,
    vector_store_id: str,
    message: str,
) -> str:
    agent = Agent(
        name=agent_name,
        model=settings.openai_model,
        instructions="Answer using this agent's knowledge base when it is relevant.",
        tools=[
            FileSearchTool(
                vector_store_ids=[vector_store_id],
                max_num_results=5,
            )
        ],
    )
    result = await Runner.run(agent, message)
    return str(result.final_output)
