from __future__ import annotations

from typing import Optional
import boto3
from botocore.client import Config
from app.core.config import settings


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name=settings.s3_region_name,
        config=Config(s3={"addressing_style": "path"}),
    )


def upload_bytes(key: str, data: bytes, content_type: Optional[str] = None) -> str:
    s3 = get_s3_client()
    extra = {"ContentType": content_type} if content_type else None
    s3.put_object(Bucket=settings.s3_bucket_name, Key=key, Body=data, **({} if not extra else extra))
    return f"s3://{settings.s3_bucket_name}/{key}"

