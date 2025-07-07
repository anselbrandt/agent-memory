import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")

if not INSTAGRAM_ACCOUNT_ID or not FACEBOOK_PAGE_ACCESS_TOKEN:
    raise ValueError(
        "Missing INSTAGRAM_ACCOUNT_ID or FACEBOOK_PAGE_ACCESS_TOKEN in .env file."
    )

# Photo post parameters
image_url = "https://s3.anselbrandt.net/chair.jpeg"
caption = "This is a chair."


async def main():

    create_url = f"https://graph.facebook.com/v23.0/{INSTAGRAM_ACCOUNT_ID}/media"
    publish_url = (
        f"https://graph.facebook.com/v23.0/{INSTAGRAM_ACCOUNT_ID}/media_publish"
    )

    create_params = {
        "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
        "image_url": image_url,
        "caption": caption,
        "format": "json",
    }

    async with httpx.AsyncClient() as client:
        try:
            create_response = await client.post(
                create_url, params=create_params, timeout=10.0
            )
            create_response.raise_for_status()
            create_data = create_response.json()

            creation_id = create_data.get("id")
            if not creation_id:
                raise httpx.HTTPStatusError(
                    status_code=400,
                    detail="No creation ID returned from Instagram API",
                )

            publish_params = {
                "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
                "creation_id": creation_id,
                "format": "json",
            }

            publish_response = await client.post(
                publish_url, params=publish_params, timeout=10.0
            )
            publish_response.raise_for_status()
            publish_data = publish_response.json()

            return {
                "success": True,
                "creation_id": creation_id,
                "post_id": publish_data.get("id"),
                "message": "Post created successfully",
            }

        except httpx.HTTPStatusError as e:
            print(f"Facebook API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
