import io
import logging
import os
from minio import Minio

_MINIO_CLIENT = Minio(
    f"{os.getenv('MINIO_HOST', 'minio')}:{os.getenv('MINIO_PORT', '9000')}",
    access_key=os.getenv('MINIO_ROOT_USER', ''),
    secret_key=os.getenv('MINIO_ROOT_PASSWORD', ''),
    secure=False,
)
_BUCKET = os.getenv('MINIO_BUCKET', 'raw')

def put_raw(source: str, key: str, data: bytes, content_type: str) -> str:
    object_key = f"{source}/{key}"
    _MINIO_CLIENT.put_object(
        _BUCKET,
        object_key,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    logging.info("Stored raw payload at %s", object_key)
    return object_key
