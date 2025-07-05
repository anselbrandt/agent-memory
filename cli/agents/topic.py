from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent
import logfire

load_dotenv()

logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_pydantic_ai()


class ChatTopic(BaseModel):
    topic: str


agent = Agent(
    "openai:gpt-4o",
    output_type=ChatTopic,
    system_prompt=(
        "Label the conversation based on the user's initial prompt. "
        "If refering to the user, always use the second person - you or you're. "
        "The topic label should be 2 to 6 words. "
    ),
)

result = agent.run_sync(
    ["Can you tell me about some famous people with the same name as me?"]
)
print(result.usage())
print(result.output.topic)
