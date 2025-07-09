import httpx

from app.models.facebook_models import (
    FacebookPagePostRequest,
    InstagramPostRequest,
    FacebookPostResponse,
    InstagramPostResponse,
)


async def post_image_to_facebook(
    facebook_post_request: FacebookPagePostRequest,
) -> FacebookPostResponse:
    post_url = (
        f"https://graph.facebook.com/v23.0/{facebook_post_request.page_id}/photos"
    )
    post_params = {
        "access_token": facebook_post_request.access_token,
        "url": facebook_post_request.image_url,
        "message": facebook_post_request.message,
        "format": "json",
    }

    async with httpx.AsyncClient() as client:
        try:
            post_response = await client.post(
                post_url, params=post_params, timeout=10.0
            )
            post_response.raise_for_status()
            post_data = post_response.json()

            return FacebookPostResponse(
                success=True,
                post_id=post_data.get("id"),
                message="Facebook post created successfully",
            )

        except httpx.HTTPStatusError as e:
            error_msg = (
                f"Facebook API error: {e.response.status_code} - {e.response.text}"
            )
            print(error_msg)
            return FacebookPostResponse(
                success=False, message="Failed to create Facebook post", error=error_msg
            )
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(error_msg)
            return FacebookPostResponse(
                success=False, message="Failed to create Facebook post", error=error_msg
            )


async def post_text_to_facebook(
    facebook_post_request: FacebookPagePostRequest,
) -> FacebookPostResponse:
    post_url = f"https://graph.facebook.com/v23.0/{facebook_post_request.page_id}/feed"
    post_params = {
        "access_token": facebook_post_request.access_token,
        "message": facebook_post_request.message,
        "format": "json",
    }

    async with httpx.AsyncClient() as client:
        try:
            post_response = await client.post(
                post_url, params=post_params, timeout=10.0
            )
            post_response.raise_for_status()
            post_data = post_response.json()

            return FacebookPostResponse(
                success=True,
                post_id=post_data.get("id"),
                message="Facebook post created successfully",
            )

        except httpx.HTTPStatusError as e:
            error_msg = (
                f"Facebook API error: {e.response.status_code} - {e.response.text}"
            )
            print(error_msg)
            return FacebookPostResponse(
                success=False, message="Failed to create Facebook post", error=error_msg
            )
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(error_msg)
            return FacebookPostResponse(
                success=False, message="Failed to create Facebook post", error=error_msg
            )


async def post_image_to_instagram(
    instagram_post_request: InstagramPostRequest,
) -> InstagramPostResponse:

    create_url = f"https://graph.facebook.com/v23.0/{instagram_post_request.instagram_account_id}/media"
    publish_url = f"https://graph.facebook.com/v23.0/{instagram_post_request.instagram_account_id}/media_publish"

    create_params = {
        "access_token": instagram_post_request.access_token,
        "image_url": instagram_post_request.image_url,
        "caption": instagram_post_request.caption,
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
                error_msg = "No creation ID returned from Instagram API"
                return InstagramPostResponse(
                    success=False,
                    message="Failed to create Instagram post",
                    error=error_msg,
                )

            publish_params = {
                "access_token": instagram_post_request.access_token,
                "creation_id": creation_id,
                "format": "json",
            }

            publish_response = await client.post(
                publish_url, params=publish_params, timeout=10.0
            )
            publish_response.raise_for_status()
            publish_data = publish_response.json()

            return InstagramPostResponse(
                success=True,
                creation_id=creation_id,
                post_id=publish_data.get("id"),
                message="Post created successfully",
            )

        except httpx.HTTPStatusError as e:
            error_msg = (
                f"Instagram API error: {e.response.status_code} - {e.response.text}"
            )
            print(error_msg)
            return InstagramPostResponse(
                success=False,
                message="Failed to create Instagram post",
                error=error_msg,
            )
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(error_msg)
            return InstagramPostResponse(
                success=False,
                message="Failed to create Instagram post",
                error=error_msg,
            )
