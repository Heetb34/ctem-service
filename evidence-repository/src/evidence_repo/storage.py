
import asyncio
import uuid
from functools import lru_cache

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from .config import get_settings


@lru_cache
def _client():
    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.s3_endpoint_url,
        region_name=s.s3_region,
        aws_access_key_id=s.s3_access_key,
        aws_secret_access_key=s.s3_secret_key,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )


def build_key(tenant_id: uuid.UUID, evidence_id: uuid.UUID) -> str:
    return f"{tenant_id}/{evidence_id}"


async def put_immutable(
    key: str,
    body: bytes,
    content_type: str,
    retention_days: int,
) -> str:
    """Put with Object Lock in COMPLIANCE mode. Returns S3 VersionId."""

    def _put() -> str:
        resp = _client().put_object(
            Bucket=get_settings().s3_bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
            ObjectLockMode="COMPLIANCE",
            ObjectLockRetainUntilDate=(
                __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                )
                + __import__("datetime").timedelta(days=retention_days)
            ),
        )
        return resp.get("VersionId", "")

    return await asyncio.to_thread(_put)


async def get_bytes(key: str, version_id: str | None = None) -> bytes:
    def _get() -> bytes:
        kwargs = {
            "Bucket": get_settings().s3_bucket,
            "Key": key,
        }

        if version_id:
            kwargs["VersionId"] = version_id

        resp = _client().get_object(**kwargs)
        return resp["Body"].read()

    return await asyncio.to_thread(_get)


async def presign_get(
    key: str,
    version_id: str | None,
    ttl_seconds: int,
) -> str:
    def _sign() -> str:
        kwargs = {
            "Bucket": get_settings().s3_bucket,
            "Key": key,
        }

        if version_id:
            kwargs["VersionId"] = version_id

        return _client().generate_presigned_url(
            "get_object",
            Params=kwargs,
            ExpiresIn=ttl_seconds,
        )

    return await asyncio.to_thread(_sign)


def object_exists(key: str, version_id: str | None = None) -> bool:
    try:
        kwargs = {
            "Bucket": get_settings().s3_bucket,
            "Key": key,
        }

        if version_id:
            kwargs["VersionId"] = version_id

        _client().head_object(**kwargs)
        return True

    except ClientError:
        return False
