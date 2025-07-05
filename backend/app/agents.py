from dataclasses import dataclass
import os

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.common_tools.tavily import tavily_search_tool

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


@dataclass
class ChatDependencies:
    todays_date: str


chat_agent = Agent(
    "openai:gpt-4o",
    tools=([tavily_search_tool(TAVILY_API_KEY)]),
    system_prompt="Use Tavily to search the web for any information you don't have access to.",
)


@chat_agent.system_prompt
async def add_current_date(ctx: RunContext[ChatDependencies]) -> str:
    todays_date = ctx.deps.todays_date
    system_prompt = (
        "Your a helpful personal assistant, you are an expert in research. "
        f"If you need today's date it is {todays_date} "
    )
    return system_prompt


class ChatTopic(BaseModel):
    topic: str


topic_agent = Agent(
    "openai:gpt-4o",
    output_type=ChatTopic,
    system_prompt=(
        "You are a friendly personal assistant. "
        "Label the conversation based on the user's initial prompt. "
        "If refering to the user, always use the second person - you or you're. "
        "Never refer to the user as 'User'. "
        "The topic label should be 2 to 6 words. "
    ),
)
