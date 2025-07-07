from pathlib import Path
import uuid
from typing import Optional

from fastapi import UploadFile
import aiofiles
import httpx
from pydantic import BaseModel

from app.config import Settings


class ImageProcessResult(BaseModel):
    """Result of image processing operation."""
    local_path: str
    filename: str
    s3_url: Optional[str] = None
    error: Optional[str] = None


class ImageService:
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.upload_url = f"{self.settings.s3_url}/upload" if self.settings.s3_url else None
        self.local_image_dir = Path("temp_images")
        self.local_image_dir.mkdir(parents=True, exist_ok=True)

    def download_image(self, image_url: str, save_dir: str = "temp_images") -> Path:
        """Download image from URL and save locally."""
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        filename = image_url.split("/")[-1].split("?")[0]
        if not any(filename.endswith(ext) for ext in [".jpg", ".jpeg", ".png"]):
            filename += ".jpg"
        file_path = Path(save_dir) / filename

        response = httpx.get(image_url)
        response.raise_for_status()
        with file_path.open("wb") as f:
            f.write(response.content)

        print(f"Image saved to {file_path}")
        return file_path

    async def upload_image_to_s3(self, file_path: Path) -> str:
        """Upload image to S3-style service."""
        if not self.settings.s3_api_token or not self.upload_url:
            raise ValueError(
                "S3 configuration not found. Please set S3_API_TOKEN and S3_URL environment variables."
            )

        async with httpx.AsyncClient() as client:
            with file_path.open("rb") as f:
                files = {"file": (file_path.name, f, "image/jpeg")}
                headers = {"x-api-token": self.settings.s3_api_token}
                response = await client.post(
                    self.upload_url, files=files, headers=headers
                )
                response.raise_for_status()
                result = response.json()
                s3_url = f"{self.settings.s3_url}/{result['url'].lstrip('/')}"
                print(f"Image uploaded to S3: {s3_url}")
                return s3_url

    async def save_uploaded_file(self, file: UploadFile) -> Path:
        """Save uploaded file to local filesystem."""
        # Generate unique filename
        file_extension = Path(file.filename or "image").suffix or ".jpg"
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = self.local_image_dir / unique_filename

        # Save file asynchronously
        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        print(f"File saved locally: {file_path}")
        return file_path

    async def process_upload(self, file: UploadFile) -> ImageProcessResult:
        """Process uploaded file: save locally and upload to S3."""
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise ValueError("File must be an image")

        try:
            # Save file locally
            local_path = await self.save_uploaded_file(file)

            result = ImageProcessResult(
                local_path=str(local_path),
                filename=local_path.name
            )

            # Try to upload to S3 if configured
            if self.settings.s3_api_token and self.settings.s3_url:
                try:
                    s3_url = await self.upload_image_to_s3(local_path)
                    result.s3_url = s3_url
                except Exception as e:
                    print(f"S3 upload failed: {e}")
                    result.error = f"S3 upload failed: {str(e)}"
            else:
                result.error = "S3 not configured - only saved locally"

            return result

        except Exception as e:
            raise ValueError(f"Failed to process upload: {str(e)}")


# Create singleton instance with settings
_settings = Settings()
image_service = ImageService(_settings)
