from dataclasses import dataclass
from typing import Optional
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
# Chat Agent with Business Context
# -------------------------


@dataclass
class BusinessInfo:
    """Business information structure matching your current model"""

    name: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None


@dataclass
class ChatDependencies:
    todays_date: str
    business_info: Optional[BusinessInfo] = None


def create_chat_agent():
    """Create chat agent with proper configuration"""
    tools = []
    if settings.tavily_api_key:
        tools.append(tavily_search_tool(api_key=settings.tavily_api_key))

    return Agent(
        model=f"openai:{settings.default_model}",
        tools=tools,
        deps_type=ChatDependencies,
    )


chat_agent = create_chat_agent()


@chat_agent.system_prompt
async def chat_system_prompt(ctx: RunContext[ChatDependencies]) -> str:
    base_prompt = (
        "You are a helpful marketing assistant and expert researcher specializing in helping businesses grow.\n"
        f"Today's date is {ctx.deps.todays_date}.\n"
        "Use Tavily to search the web when you need up-to-date information about markets, competitors, or trends.\n"
    )

    # Add business context if available
    if ctx.deps.business_info:
        business = ctx.deps.business_info
        business_context = "\n--- CLIENT BUSINESS CONTEXT ---\n"

        if business.name:
            business_context += f"Business Name: {business.name}\n"
        if business.url:
            business_context += f"Website: {business.url}\n"
        if business.description:
            business_context += f"Business Description: {business.description}\n"

        business_context += (
            "\nWhen providing marketing advice, content suggestions, competitive analysis, or research insights, "
            "always consider this specific business context. Tailor your responses to be directly relevant "
            "and actionable for this business. If you need to research competitors or market trends, "
            "use the business name and description to focus your search queries.\n"
        )

        base_prompt += business_context
    else:
        base_prompt += (
            "\nNote: No specific business context is available. Provide general marketing advice "
            "and ask clarifying questions about the user's business when relevant.\n"
        )

    return base_prompt


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
