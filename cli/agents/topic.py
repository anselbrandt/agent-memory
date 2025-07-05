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
        "Label the chat exchange with a descriptive topic "
        "If refering to the user, always use the second person - you or you're. "
        "The topic label should be 2 to 6 words. "
    ),
)

result = agent.run_sync(
    [
        "Can you tell me about some famous people with the same name as me? "
        "Of course! However, I would need to know your name to provide information about famous people who share it. Could you please tell me your name?"
    ]
)
print(result.output)
print(result.usage())
