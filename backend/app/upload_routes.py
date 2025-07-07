from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.image_service import image_service


class ImageUploadResponse(BaseModel):
    """Response model for image upload."""
    success: bool
    message: str
    data: dict


router = APIRouter(prefix="/upload", tags=["upload"])


def get_authenticated_user_id(request: Request) -> tuple[str, bool]:
    """Get the authenticated user ID from session.
    
    Returns:
        tuple: (user_id, is_authenticated) - user_id and whether they're actually authenticated
    """
    try:
        from app.auth_service import auth_service

        session_id = request.cookies.get("session_id")
        if session_id:
            user_data = auth_service.get_session_user(session_id)
            if user_data:
                return user_data.get("id"), True
    except ImportError:
        pass

    return None, False


@router.post("/image")
async def upload_image(
    request: Request,
    file: UploadFile = File(...)
) -> ImageUploadResponse:
    """Upload an image file for use in social media posts."""
    
    _, is_authenticated = get_authenticated_user_id(request)
    
    if not is_authenticated:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    try:
        result = await image_service.process_upload(file)

        return ImageUploadResponse(
            success=True,
            message="Image uploaded successfully",
            data={
                "filename": result.filename,
                "local_path": result.local_path,
                "s3_url": result.s3_url,
                "public_url": result.s3_url or f"/api/upload/image/{result.filename}",
                "upload_error": result.error,
            }
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/image/{filename}")
async def get_image(filename: str) -> FileResponse:
    """Serve locally stored images."""
    
    # Validate filename to prevent directory traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    image_path = Path("temp_images") / filename

    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Determine media type based on file extension
    media_type = "image/jpeg"  # default
    if filename.lower().endswith(".png"):
        media_type = "image/png"
    elif filename.lower().endswith(".gif"):
        media_type = "image/gif"
    elif filename.lower().endswith(".webp"):
        media_type = "image/webp"

    return FileResponse(
        path=str(image_path),
        media_type=media_type,
        filename=filename
    )
