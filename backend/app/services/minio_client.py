"""
EDM v2.1 — MinIO / S3-compatible object-store wrapper.
Provides upload, download, and bucket-creation helpers.
"""
from __future__ import annotations

import logging
import os
from io import BytesIO
from typing import Optional

from minio import Minio
from minio.error import S3Error

from app.config import settings

logger = logging.getLogger("edm.minio")

RAW_UPLOADS_BUCKET = "raw-uploads"
# Ensure bucket exists on startup (called in app lifespan or at import time)


def _get_client() -> Minio:
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


# Singleton client
_minio_client: Optional[Minio] = None


def get_minio_client() -> Minio:
    global _minio_client
    if _minio_client is None:
        _minio_client = _get_client()
    return _minio_client


def ensure_bucket_exists(bucket_name: str = RAW_UPLOADS_BUCKET) -> None:
    """Create bucket if it does not already exist."""
    client = get_minio_client()
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            logger.info("Created MinIO bucket '%s'", bucket_name)
        else:
            logger.debug("MinIO bucket '%s' already exists", bucket_name)
    except S3Error as exc:
        logger.error("Failed to ensure bucket '%s' exists: %s", bucket_name, exc)
        raise


def upload_bytes(data: bytes, object_key: str, bucket: str = RAW_UPLOADS_BUCKET) -> None:
    """Upload raw bytes to MinIO."""
    client = get_minio_client()
    length = len(data)
    client.put_object(bucket, object_key, BytesIO(data), length)
    logger.info("Uploaded object '%s' to bucket '%s' (%d bytes)", object_key, bucket, length)


def download_bytes(object_key: str, bucket: str = RAW_UPLOADS_BUCKET) -> bytes:
    """Download an object from MinIO and return raw bytes."""
    client = get_minio_client()
    response = client.get_object(bucket, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()
