from dataclasses import dataclass
import os

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.common_tools.tavily import tavily_search_tool

from app.config import Settings

settings = Settings()

# Set environment variables for pydantic-ai
if settings.openai_api_key:
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key

# -------------------------
# Chat Agent with Tavily Search
# -------------------------


@dataclass
class ChatDependencies:
    todays_date: str


def create_chat_agent():
    """Create chat agent with proper configuration"""
    tools = []
    if settings.tavily_api_key:
        tools.append(tavily_search_tool(api_key=settings.tavily_api_key))
    
    return Agent(
        model=f"openai:{settings.default_model}",
        tools=tools,
    )


chat_agent = create_chat_agent()


@chat_agent.system_prompt
async def chat_system_prompt(ctx: RunContext[ChatDependencies]) -> str:
    return (
        "You are a helpful personal assistant and expert researcher.\n"
        f"Today's date is {ctx.deps.todays_date}.\n"
        "Use Tavily to search the web when you need up-to-date information."
    )


# -------------------------
# Topic Labeling Agent
# -------------------------


class ChatTopic(BaseModel):
    topic: str


topic_agent = Agent(
    model=f"openai:{settings.default_model}",
    output_type=ChatTopic,
    system_prompt=(
        "You are a friendly personal assistant.\n"
        "Label the conversation based on the user's initial message.\n"
        "Always refer to the user as 'you' or 'you're'; never say 'User'.\n"
        "Output a concise topic label (2 to 6 words)."
    ),
)
