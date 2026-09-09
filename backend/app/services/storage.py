"""Object storage adapter — private bucket, presigned URLs only.

owner: Backend/Infra

Wraps an S3-compatible client (AWS S3, Cloudflare R2, or local MinIO for dev) so
callers never touch bucket credentials or raw bytes directly. The bucket is
private; uploads/downloads go through short-lived presigned URLs. Never log
image bytes, and never put a raw key or signed URL for a user photo into
application logs.

Configured entirely from `app.config.settings` (STORAGE_*): a blank
STORAGE_ENDPOINT_URL targets AWS S3; a populated one targets an S3-compatible
endpoint (R2, MinIO) using path-style addressing.
"""

from functools import lru_cache

import boto3
from botocore.client import Config

from app.config import settings

DEFAULT_EXPIRES_SECONDS = 900  # 15 minutes


@lru_cache
def _client():
    if settings.STORAGE_ENDPOINT_URL:
        # R2 / MinIO: custom endpoint, path-style addressing.
        config = Config(signature_version="s3v4", s3={"addressing_style": "path"})
    else:
        config = Config(signature_version="s3v4")

    return boto3.client(
        "s3",
        aws_access_key_id=settings.STORAGE_ACCESS_KEY or None,
        aws_secret_access_key=settings.STORAGE_SECRET_KEY or None,
        region_name=settings.STORAGE_REGION,
        endpoint_url=settings.STORAGE_ENDPOINT_URL or None,
        config=config,
    )


def presigned_upload_url(
    key: str, content_type: str, expires_seconds: int = DEFAULT_EXPIRES_SECONDS
) -> str:
    """Short-lived URL the caller can PUT the raw file to directly (bypasses the API)."""
    return _client().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.STORAGE_BUCKET, "Key": key, "ContentType": content_type},
        ExpiresIn=expires_seconds,
    )


def presigned_download_url(key: str, expires_seconds: int = DEFAULT_EXPIRES_SECONDS) -> str:
    """Short-lived URL to read a private object — this is what `*_url` fields serve."""
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.STORAGE_BUCKET, "Key": key},
        ExpiresIn=expires_seconds,
    )


def upload_bytes(key: str, data: bytes, content_type: str) -> None:
    """Upload bytes server-side (used by the worker for processed cutouts).

    Never log `data`.
    """
    _client().put_object(
        Bucket=settings.STORAGE_BUCKET, Key=key, Body=data, ContentType=content_type
    )
