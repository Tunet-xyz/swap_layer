import hashlib
import mimetypes
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, BinaryIO

from django.conf import settings

from ..adapter import (
    StorageCopyError,
    StorageDeleteError,
    StorageDownloadError,
    StorageFileNotFoundError,
    StorageMoveError,
    StorageProviderAdapter,
    StorageUploadError,
)


class LocalFileStorageProvider(StorageProviderAdapter):
    """
    Local filesystem storage provider.
    Stores files in a local directory structure.
    """

    def __init__(self, base_path: str | None = None, base_url: str | None = None):
        """
        Initialize local file storage provider.

        Args:
            base_path: Base directory for file storage (defaults to MEDIA_ROOT)
            base_url: Base URL for accessing files (defaults to MEDIA_URL)
        """
        self.base_path = Path(base_path or getattr(settings, "MEDIA_ROOT", "media"))
        self.base_url = base_url or getattr(settings, "MEDIA_URL", "/media/")

        # Ensure base path exists
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, file_path: str) -> Path:
        """Get the full filesystem path for a file."""
        return self.base_path / file_path

    def _calculate_etag(self, file_path: Path) -> str:
        """Calculate an ETag (MD5 hash) for a file."""
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()

    def upload_file(
        self,
        file_path: str,
        file_data: BinaryIO,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
        public: bool = False,
    ) -> dict[str, Any]:
        """Upload a file to local storage."""
        try:
            full_path = self._get_full_path(file_path)
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the file
            with open(full_path, "wb") as f:
                if hasattr(file_data, "read"):
                    shutil.copyfileobj(file_data, f)
                else:
                    f.write(file_data)

            # Get file info
            file_size = full_path.stat().st_size
            etag = self._calculate_etag(full_path)

            # Store metadata in a sidecar file if provided
            if metadata:
                metadata_path = full_path.with_suffix(full_path.suffix + ".meta")
                with open(metadata_path, "w") as f:
                    for key, value in metadata.items():
                        f.write(f"{key}:{value}\n")

            return {
                "url": self.get_file_url(file_path),
                "file_path": file_path,
                "size": file_size,
                "content_type": content_type or "application/octet-stream",
                "etag": etag,
            }
        except Exception as e:
            raise StorageUploadError(f"Failed to upload file: {str(e)}")

    def download_file(self, file_path: str, destination: str | None = None) -> bytes:
        """Download a file from local storage."""
        try:
            full_path = self._get_full_path(file_path)

            if not full_path.exists():
                raise StorageFileNotFoundError(f"File not found: {file_path}")

            if destination:
                shutil.copy2(full_path, destination)
                return b""
            else:
                with open(full_path, "rb") as f:
                    return f.read()
        except StorageFileNotFoundError:
            raise
        except Exception as e:
            raise StorageDownloadError(f"Failed to download file: {str(e)}")

    def delete_file(self, file_path: str) -> dict[str, Any]:
        """Delete a file from local storage."""
        try:
            full_path = self._get_full_path(file_path)

            if not full_path.exists():
                raise StorageFileNotFoundError(f"File not found: {file_path}")

            # Delete metadata file if it exists
            metadata_path = full_path.with_suffix(full_path.suffix + ".meta")
            if metadata_path.exists():
                metadata_path.unlink()

            full_path.unlink()

            return {
                "deleted": True,
                "file_path": file_path,
            }
        except StorageFileNotFoundError:
            raise
        except Exception as e:
            raise StorageDeleteError(f"Failed to delete file: {str(e)}")

    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists in local storage."""
        full_path = self._get_full_path(file_path)
        return full_path.exists() and full_path.is_file()

    def get_file_metadata(self, file_path: str) -> dict[str, Any]:
        """Get metadata for a file."""
        full_path = self._get_full_path(file_path)

        if not full_path.exists():
            raise StorageFileNotFoundError(f"File not found: {file_path}")

        stat = full_path.stat()
        etag = self._calculate_etag(full_path)

        # Load custom metadata if it exists
        custom_metadata = {}
        metadata_path = full_path.with_suffix(full_path.suffix + ".meta")
        if metadata_path.exists():
            with open(metadata_path) as f:
                for line in f:
                    if ":" in line:
                        key, value = line.strip().split(":", 1)
                        custom_metadata[key] = value

        # Detect content type from file extension
        content_type, _ = mimetypes.guess_type(str(full_path))
        if not content_type:
            content_type = "application/octet-stream"

        return {
            "size": stat.st_size,
            "content_type": content_type,
            "last_modified": datetime.fromtimestamp(stat.st_mtime),
            "etag": etag,
            "metadata": custom_metadata,
        }

    def list_files(
        self, prefix: str | None = None, max_results: int = 1000
    ) -> list[dict[str, Any]]:
        """List files in local storage."""
        results = []
        search_path = self._get_full_path(prefix) if prefix else self.base_path

        if not search_path.exists():
            return results

        for file_path in search_path.rglob("*"):
            if file_path.is_file() and not file_path.suffix == ".meta":
                relative_path = str(file_path.relative_to(self.base_path))
                stat = file_path.stat()
                etag = self._calculate_etag(file_path)

                results.append(
                    {
                        "file_path": relative_path,
                        "size": stat.st_size,
                        "last_modified": datetime.fromtimestamp(stat.st_mtime),
                        "etag": etag,
                    }
                )

                if len(results) >= max_results:
                    break

        return results

    def get_file_url(self, file_path: str, expiration: timedelta | None = None) -> str:
        """Get a URL to access a file."""
        # Local files don't support signed URLs, just return the direct URL
        # Note: expiration parameter is ignored for local storage
        return f"{self.base_url.rstrip('/')}/{file_path}"

    def generate_presigned_upload_url(
        self,
        file_path: str,
        content_type: str | None = None,
        expiration: timedelta = timedelta(hours=1),
    ) -> dict[str, Any]:
        """
        Generate a presigned URL for direct upload.

        Note: Local storage doesn't support presigned uploads.
        This returns a placeholder that indicates server-side upload is required.
        """
        return {
            "url": None,  # Indicates server-side upload required
            "fields": {},
            "method": "POST",
            "message": "Local storage requires server-side upload",
        }

    def copy_file(self, source_path: str, destination_path: str) -> dict[str, Any]:
        """Copy a file within local storage."""
        try:
            source_full_path = self._get_full_path(source_path)
            destination_full_path = self._get_full_path(destination_path)

            if not source_full_path.exists():
                raise StorageFileNotFoundError(f"Source file not found: {source_path}")

            destination_full_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_full_path, destination_full_path)

            # Copy metadata if it exists
            source_metadata_path = source_full_path.with_suffix(source_full_path.suffix + ".meta")
            if source_metadata_path.exists():
                destination_metadata_path = destination_full_path.with_suffix(
                    destination_full_path.suffix + ".meta"
                )
                shutil.copy2(source_metadata_path, destination_metadata_path)

            etag = self._calculate_etag(destination_full_path)

            return {
                "source_path": source_path,
                "destination_path": destination_path,
                "etag": etag,
            }
        except StorageFileNotFoundError:
            raise
        except Exception as e:
            raise StorageCopyError(f"Failed to copy file: {str(e)}")

    def move_file(self, source_path: str, destination_path: str) -> dict[str, Any]:
        """Move/rename a file within local storage."""
        try:
            source_full_path = self._get_full_path(source_path)
            destination_full_path = self._get_full_path(destination_path)

            if not source_full_path.exists():
                raise StorageFileNotFoundError(f"Source file not found: {source_path}")

            destination_full_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_full_path), str(destination_full_path))

            # Move metadata if it exists
            source_metadata_path = source_full_path.with_suffix(source_full_path.suffix + ".meta")
            if source_metadata_path.exists():
                destination_metadata_path = destination_full_path.with_suffix(
                    destination_full_path.suffix + ".meta"
                )
                shutil.move(str(source_metadata_path), str(destination_metadata_path))

            return {
                "source_path": source_path,
                "destination_path": destination_path,
            }
        except StorageFileNotFoundError:
            raise
        except Exception as e:
            raise StorageMoveError(f"Failed to move file: {str(e)}")

    def delete_files(self, file_paths: list[str]) -> dict[str, Any]:
        """Delete multiple files from local storage."""
        deleted = []
        errors = []

        for file_path in file_paths:
            try:
                self.delete_file(file_path)
                deleted.append(file_path)
            except Exception as e:
                errors.append(
                    {
                        "file_path": file_path,
                        "error": str(e),
                    }
                )

        return {
            "deleted": deleted,
            "errors": errors,
        }
