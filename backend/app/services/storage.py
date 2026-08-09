import os
from abc import ABC, abstractmethod
from typing import Generator
import boto3
from app.core.config import settings

class StorageService(ABC):
    @abstractmethod
    def upload_file(self, file_content: bytes, destination_path: str) -> str:
        """
        Uploads file content to the store and returns the relative file identifier/path.
        """
        pass

    @abstractmethod
    def download_file(self, file_path: str) -> bytes:
        """
        Downloads files from the store and returns binary content.
        """
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        """
        Deletes a file from the store. Returns true if successful.
        """
        pass

class LocalStorageService(StorageService):
    def __init__(self, base_dir: str = settings.LOCAL_STORAGE_DIR):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_safe_path(self, file_path: str) -> str:
        # Prevent directory traversal attacks
        target_path = os.path.abspath(os.path.join(self.base_dir, file_path))
        if not target_path.startswith(self.base_dir):
            raise ValueError(f"Path traversal attempt blocked: {file_path}")
        return target_path

    def upload_file(self, file_content: bytes, destination_path: str) -> str:
        safe_path = self._get_safe_path(destination_path)
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        with open(safe_path, "wb") as f:
            f.write(file_content)
        return destination_path

    def download_file(self, file_path: str) -> bytes:
        safe_path = self._get_safe_path(file_path)
        if not os.path.exists(safe_path):
            raise FileNotFoundError(f"File not found in storage: {file_path}")
        with open(safe_path, "rb") as f:
            return f.read()

    def delete_file(self, file_path: str) -> bool:
        try:
            safe_path = self._get_safe_path(file_path)
            if os.path.exists(safe_path):
                os.remove(safe_path)
                return True
            return False
        except Exception:
            return False

class S3StorageService(StorageService):
    def __init__(self):
        self.bucket = settings.S3_BUCKET_NAME
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            endpoint_url=settings.S3_ENDPOINT_URL,
            region_name=settings.S3_REGION
        )

    def upload_file(self, file_content: bytes, destination_path: str) -> str:
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=destination_path,
            Body=file_content
        )
        return destination_path

    def download_file(self, file_path: str) -> bytes:
        response = self.s3_client.get_object(
            Bucket=self.bucket,
            Key=file_path
        )
        return response["Body"].read()

    def delete_file(self, file_path: str) -> bool:
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket,
                Key=file_path
            )
            return True
        except Exception:
            return False

def get_storage_service() -> StorageService:
    """
    Returns the appropriate StorageService based on configuration setting.
    """
    if settings.STORAGE_PROVIDER == "s3":
        return S3StorageService()
    return LocalStorageService()
