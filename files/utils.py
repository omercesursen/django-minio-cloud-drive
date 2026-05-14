from minio import Minio
from django.conf import settings


minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_USE_SSL
)

if not minio_client.bucket_exists(settings.MINIO_BUCKET_NAME):
    minio_client.make_bucket(settings.MINIO_BUCKET_NAME)