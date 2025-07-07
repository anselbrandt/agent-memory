import os
import asyncio
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")

# Validate environment variables
if not FACEBOOK_PAGE_ID or not FACEBOOK_PAGE_ACCESS_TOKEN:
    raise ValueError(
        "Missing FACEBOOK_PAGE_ID or FACEBOOK_PAGE_ACCESS_TOKEN in .env file."
    )

# Photo post parameters
message = "This is text."


async def main():
    post_url = f"https://graph.facebook.com/v23.0/{FACEBOOK_PAGE_ID}/feed"
    post_params = {
        "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
        "message": message,
        "format": "json",
    }

    async with httpx.AsyncClient() as client:
        try:
            post_response = await client.post(
                post_url, params=post_params, timeout=10.0
            )
            post_response.raise_for_status()
            post_data = post_response.json()

            print(
                {
                    "success": True,
                    "post_id": post_data.get("id"),
                    "message": "Facebook post created successfully",
                }
            )

        except httpx.HTTPStatusError as e:
            print(f"Facebook API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
