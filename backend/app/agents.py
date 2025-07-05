from dataclasses import dataclass
import os

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.common_tools.tavily import tavily_search_tool

load_dotenv()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# -------------------------
# Chat Agent with Tavily Search
# -------------------------


@dataclass
class ChatDependencies:
    todays_date: str


chat_agent = Agent(
    model="openai:gpt-4o",
    tools=[tavily_search_tool(api_key=TAVILY_API_KEY)],
)


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
    model="openai:gpt-4o",
    output_type=ChatTopic,
    system_prompt=(
        "You are a friendly personal assistant.\n"
        "Label the conversation based on the user's initial message.\n"
        "Always refer to the user as 'you' or 'you're'; never say 'User'.\n"
        "Output a concise topic label (2 to 6 words)."
    ),
)
