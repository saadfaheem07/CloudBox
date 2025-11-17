from sqlalchemy import create_engine, text
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import uuid
import os

import boto3
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

app = FastAPI(title="CloudBox - File Storage Lite")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# DATABASE SETUP
# ---------------------------
engine = create_engine(os.getenv("DATABASE_URL"))

# ---------------------------
# AWS S3 CLIENT
# ---------------------------
from botocore.config import Config

s3_config = Config(
    region_name=os.getenv("AWS_REGION"),
    signature_version="s3v4",
    retries={'max_attempts': 10, 'mode': 'standard'},
    s3={'addressing_style': 'virtual'}
)

s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION"),
    config=s3_config
)

s3_client = boto3.client(
    "s3",
    config=s3_config,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)
S3_BUCKET = os.getenv("S3_BUCKET_NAME")

# ---------------------------
# SIMPLE AUTH (TEMP)
# ---------------------------
def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """
    TEMP AUTH:
    For now:
        Authorization: Fake <user_id>
    Example:
        Authorization: Fake 11111111-2222-3333-4444-555555555555
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization")

    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "fake":
        return parts[1]

    raise HTTPException(status_code=401, detail="Invalid Authorization format")

# ---------------------------
# REQUEST MODELS
# ---------------------------
class PresignUploadRequest(BaseModel):
    file_name: str
    folder_id: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None

class PresignUploadResponse(BaseModel):
    file_id: str
    upload_url: str

class ShareRequest(BaseModel):
    expires_in_hours: int = 24
    max_downloads: Optional[int] = None

class ShareResponse(BaseModel):
    public_url: str

# ---------------------------
# HELPER METHOD
# ---------------------------
def create_file_record(user_id: str, req: PresignUploadRequest, s3_key: str, file_id: str):
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO files (
                    id, owner_id, folder_id, original_name,
                    s3_key, mime_type, size_bytes
                ) VALUES (
                    :id, :owner_id, :folder_id, :original_name,
                    :s3_key, :mime_type, :size_bytes
                )
            """),
            {
                "id": file_id,
                "owner_id": user_id,
                "folder_id": req.folder_id,
                "original_name": req.file_name,
                "s3_key": s3_key,
                "mime_type": req.mime_type,
                "size_bytes": req.size_bytes,
            },
        )

# ---------------------------
# ROUTES
# ---------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

# ----- PRESIGNED UPLOAD -----
@app.post("/files/presign-upload", response_model=PresignUploadResponse)
def presign_upload(body: PresignUploadRequest, user_id: str = Depends(get_current_user)):

    # If folder_id is provided, validate it belongs to this user
    if body.folder_id is not None:
        with engine.begin() as conn:
            folder = conn.execute(
                text("""
                    SELECT id FROM folders
                    WHERE id = :id AND owner_id = :owner_id
                """),
                {"id": body.folder_id, "owner_id": user_id}
            ).fetchone()

        if not folder:
            raise HTTPException(status_code=400, detail="Invalid folder_id or unauthorized access")

    # Generate a new file ID
    file_id = str(uuid.uuid4())

    # Put file inside folder subpath, like:
    # users/<user>/<folder>/<file_id>/<original_name>
    folder_path = body.folder_id if body.folder_id else "root"

    s3_key = f"users/{user_id}/{folder_path}/{file_id}/{body.file_name}"

    # Insert into DB
    create_file_record(user_id, body, s3_key, file_id)

    try:
        url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": S3_BUCKET,
                "Key": s3_key,
                "ContentType": body.mime_type or "application/octet-stream"
            },
            ExpiresIn=3600
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return PresignUploadResponse(file_id=file_id, upload_url=url)

from sqlalchemy import text

@app.get("/files/list")
def list_files(
    folder_id: Optional[str] = None,
    user_id: str = Depends(get_current_user),
):
    try:
        with engine.connect() as conn:

            # Root folder means folder_id = NULL
            if folder_id == "null" or folder_id is None:
                query = text("""
                    SELECT id AS file_id,
                           original_name AS file_name,
                           size_bytes,
                           folder_id
                    FROM files
                    WHERE owner_id = :owner_id
                      AND deleted_at IS NULL
                      AND folder_id IS NULL
                    ORDER BY original_name;
                """)
                rows = conn.execute(query, {"owner_id": user_id}).mappings().all()

            else:
                # For specific folder
                query = text("""
                    SELECT id AS file_id,
                           original_name AS file_name,
                           size_bytes,
                           folder_id
                    FROM files
                    WHERE owner_id = :owner_id
                      AND deleted_at IS NULL
                      AND folder_id = :folder_id
                    ORDER BY original_name;
                """)
                rows = conn.execute(
                    query,
                    {"owner_id": user_id, "folder_id": folder_id},
                ).mappings().all()

    except Exception as e:
        print("ERROR in /files/list:", repr(e))
        raise HTTPException(status_code=500, detail="Failed to list files")

    return {"files": list(rows)}

# ----- DOWNLOAD URL -----
@app.get("/files/{file_id}/download-url")
def get_download_url(file_id: str, user_id: str = Depends(get_current_user)):
    # Fetch file metadata
    with engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT s3_key, owner_id
                FROM files
                WHERE id = :id AND deleted_at IS NULL
            """),
            {"id": file_id},
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="File not found")

    s3_key, owner_id = row

    # TEMP: log for debugging, but do NOT block download
    if owner_id != user_id:
        print("DEBUG owner mismatch:")
        print(f"  owner_id in DB: {owner_id}")
        print(f"  user_id from token: {user_id}")
        # You *could* still block here later if you want

    # Generate presigned GET URL
    url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": s3_key},
        ExpiresIn=600,  # 10 minutes
    )

    return {"url": url}

# ----- CREATE SHARE LINK -----
@app.post("/files/{file_id}/share", response_model=ShareResponse)
def create_share_link(file_id: str, body: ShareRequest, user_id: str = Depends(get_current_user)):

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT owner_id FROM files WHERE id = :id AND deleted_at IS NULL"),
            {"id": file_id},
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="File not found")

    owner_id = row[0]
    if owner_id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    token = uuid.uuid4().hex
    share_id = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=body.expires_in_hours)

    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO share_links (
                    id, file_id, token, expires_at, max_downloads
                ) VALUES (
                    :id, :file_id, :token, :expires_at, :max_downloads
                )
            """),
            {
                "id": share_id,
                "file_id": file_id,
                "token": token,
                "expires_at": expires_at,
                "max_downloads": body.max_downloads
            },
        )

    return ShareResponse(public_url=f"http://localhost:8000/share/{token}")

# ----- PUBLIC SHARE ACCESS -----
@app.get("/share/{token}")
def access_shared_file(token: str):

    with engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT sl.id, sl.file_id, sl.expires_at,
                       sl.max_downloads, sl.download_count,
                       f.s3_key
                FROM share_links sl
                JOIN files f ON f.id = sl.file_id
                WHERE sl.token = :token AND f.deleted_at IS NULL
            """),
            {"token": token},
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Invalid or expired link")

    share_id, file_id, expires_at, max_downloads, download_count, s3_key = row

    if datetime.utcnow() > expires_at:
        raise HTTPException(status_code=410, detail="Link expired")

    if max_downloads is not None and download_count >= max_downloads:
        raise HTTPException(status_code=429, detail="Download limit reached")

    # increment download count
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE share_links
                SET download_count = download_count + 1
                WHERE id = :id
            """),
            {"id": share_id},
        )

    url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": s3_key},
        ExpiresIn=600
    )

    return {"url": url}

# ===========================
# CREATE FOLDER
# ===========================
class CreateFolderRequest(BaseModel):
    name: str
    parent_folder_id: Optional[str] = None

class CreateFolderResponse(BaseModel):
    folder_id: str

@app.post("/folders", response_model=CreateFolderResponse)
def create_folder(body: CreateFolderRequest, user_id: str = Depends(get_current_user)):
    folder_id = str(uuid.uuid4())

    # Insert into DB
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO folders (id, owner_id, name, parent_folder_id)
                VALUES (:id, :owner_id, :name, :parent_folder_id)
            """),
            {
                "id": folder_id,
                "owner_id": user_id,
                "name": body.name,
                "parent_folder_id": body.parent_folder_id
            }
        )

    return CreateFolderResponse(folder_id=folder_id)

# ===========================
# LIST FOLDER CONTENTS
# ===========================
@app.get("/folders/{folder_id}/contents")
def list_folder_contents(folder_id: str, user_id: str = Depends(get_current_user)):

    # Interpret "root"
    parent_id = None if folder_id == "root" else folder_id

    with engine.begin() as conn:

        # List folders
        folders = conn.execute(
            text("""
                SELECT id, name, created_at
                FROM folders
                WHERE owner_id = :owner_id
                  AND parent_folder_id IS NOT DISTINCT FROM :parent_folder_id
                ORDER BY created_at ASC
            """),
            {"owner_id": user_id, "parent_folder_id": parent_id}
        ).fetchall()

        # List files
        files = conn.execute(
            text("""
                SELECT id, original_name, size_bytes, created_at
                FROM files
                WHERE owner_id = :owner_id
                  AND folder_id IS NOT DISTINCT FROM :folder_id
                  AND deleted_at IS NULL
                ORDER BY created_at ASC
            """),
            {"owner_id": user_id, "folder_id": parent_id}
        ).fetchall()

    return {
        "folders": [
            {"id": f.id, "name": f.name, "created_at": f.created_at.isoformat()}
            for f in folders
        ],
        "files": [
            {
                "id": x.id,
                "name": x.original_name,
                "size": x.size_bytes,
                "created_at": x.created_at.isoformat()
            }
            for x in files
        ]
    }

# ===========================
# DELETE FOLDER (SOFT DELETE)
# ===========================
@app.delete("/folders/{folder_id}")
def delete_folder(folder_id: str, user_id: str = Depends(get_current_user)):

    with engine.begin() as conn:
        # Ensure folder exists AND user owns it
        exists = conn.execute(
            text("""
                SELECT 1 FROM folders
                WHERE id = :id AND owner_id = :owner_id
            """),
            {"id": folder_id, "owner_id": user_id}
        ).fetchone()

        if not exists:
            raise HTTPException(status_code=404, detail="Folder not found")

        # Delete it
        conn.execute(
            text("DELETE FROM folders WHERE id = :id"),
            {"id": folder_id}
        )

    return {"status": "deleted"}

