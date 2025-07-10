from pathlib import Path
import os
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Optional

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

STATIC_DIR = Path("static")
STATIC_DIR.mkdir(parents=True, exist_ok=True)

origins = [
    "http://localhost:3000",
    "https://air.anselbrandt.net",
]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Hello, from S3"}


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...), x_api_token: Optional[str] = Header(None)
):
    if x_api_token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing API token")

    try:
        filename = file.filename
        filepath = STATIC_DIR / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "wb") as f:
            content = await file.read()
            f.write(content)

        return {
            "status": "success",
            "filename": filename,
            "url": f"/{filename}",  # relative URL for static mount
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
