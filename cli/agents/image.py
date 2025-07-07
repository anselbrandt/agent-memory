import asyncio

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent, ImageUrl
import logfire

load_dotenv()

logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_pydantic_ai()


class ImageDescription(BaseModel):
    description: str


agent = Agent(
    "openai:gpt-4o",
    output_type=ImageDescription,
    system_prompt=(
        "You are an expert at describing images in detail. "
        "Generate a comprehensive description of the provided image."
    ),
)


async def main():
    async with agent.run_stream(
        [
            ImageUrl(url="https://s3.anselbrandt.net/chair.jpeg"),
        ]
    ) as response:
        result = await response.get_output()
        description = result.description
        print(description)


if __name__ == "__main__":
    asyncio.run(main())
