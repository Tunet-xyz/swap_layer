from typing import Any, BinaryIO

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from ..adapter import (
    StorageDeleteError,
    StorageDownloadError,
    StorageProviderAdapter,
    StorageUploadError,
)


class DjangoStorageAdapter(StorageProviderAdapter):
    """
    Storage provider that wraps Django's default storage system.
    This allows using any backend supported by django-storages (S3, Azure, GCloud, etc.)
    or the local filesystem, configured via standard Django settings.
    """

    def upload_file(
        self,
        file_path: str,
        file_data: BinaryIO,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
        public: bool = False,
    ) -> dict[str, Any]:
        try:
            # Django storage saves the file and returns the name
            saved_path = default_storage.save(file_path, file_data)

            # Try to get the URL, might fail for some backends
            try:
                url = default_storage.url(saved_path)
            except NotImplementedError:
                url = None

            # Get size if possible
            try:
                size = default_storage.size(saved_path)
            except NotImplementedError:
                size = None

            return {
                "url": url,
                "file_path": saved_path,
                "size": size,
                "content_type": content_type,
                # Note: metadata support varies widely by backend in Django
            }
        except Exception as e:
            raise StorageUploadError(f"Failed to upload file: {str(e)}") from e

    def download_file(self, file_path: str, destination: str | None = None) -> bytes:
        from ..adapter import StorageFileNotFoundError

        try:
            if not default_storage.exists(file_path):
                raise StorageFileNotFoundError(f"File not found: {file_path}")

            with default_storage.open(file_path, "rb") as f:
                content = f.read()

            if destination:
                with open(destination, "wb") as f:
                    f.write(content)

            return content
        except StorageFileNotFoundError:
            raise
        except Exception as e:
            raise StorageDownloadError(f"Failed to download file: {str(e)}") from e

    def delete_file(self, file_path: str) -> dict[str, Any]:
        try:
            if default_storage.exists(file_path):
                default_storage.delete(file_path)
                return {"deleted": True, "file_path": file_path}
            from ..adapter import StorageFileNotFoundError

            raise StorageFileNotFoundError(f"File not found: {file_path}")
        except StorageFileNotFoundError:
            raise
        except Exception as e:
            raise StorageDeleteError(f"Failed to delete file: {str(e)}") from e

    def get_file_url(self, file_path: str, expiry_seconds: int = 3600) -> str:
        try:
            # Note: expiry_seconds might be ignored by some backends or require specific config
            return default_storage.url(file_path)
        except Exception:
            # Fallback or re-raise depending on strictness needed
            return ""

    def list_files(self, prefix: str = "") -> dict[str, Any]:
        try:
            directories, files = default_storage.listdir(prefix)
            return {"files": files, "directories": directories}
        except Exception:
            # Some backends don't support listing
            return {"files": [], "directories": []}

    def file_exists(self, file_path: str) -> bool:
        return default_storage.exists(file_path)

    def get_file_metadata(self, file_path: str) -> dict[str, Any]:
        try:
            return {
                "size": default_storage.size(file_path),
                "modified_time": default_storage.get_modified_time(file_path),
                "created_time": default_storage.get_created_time(file_path),
            }
        except Exception:
            return {}

    def generate_presigned_upload_url(
        self, file_path: str, content_type: str | None = None, expiration: int = 3600
    ) -> dict[str, Any]:
        """
        Generate a presigned URL for direct upload.
        Note: Not all Django storage backends support this (e.g., S3 does, local doesn't).
        """
        # Most Django storages don't have presigned URL support
        # This would need to be implemented per-backend or with django-storages extras
        raise NotImplementedError(
            "Presigned URLs are not universally supported by Django storages. "
            "Use a provider-specific implementation or django-storages with S3."
        )

    def copy_file(self, source_path: str, destination_path: str) -> dict[str, Any]:
        """Copy a file within storage."""
        from ..adapter import StorageCopyError, StorageFileNotFoundError

        try:
            if not default_storage.exists(source_path):
                raise StorageFileNotFoundError(f"Source file not found: {source_path}")

            # Read and write (Django storage doesn't have native copy)
            with default_storage.open(source_path, "rb") as source:
                content = source.read()
                default_storage.save(destination_path, ContentFile(content))

            return {
                "source_path": source_path,
                "destination_path": destination_path,
            }
        except StorageFileNotFoundError:
            raise
        except Exception as e:
            raise StorageCopyError(f"Failed to copy file: {str(e)}") from e

    def move_file(self, source_path: str, destination_path: str) -> dict[str, Any]:
        """Move/rename a file within storage."""
        from ..adapter import StorageFileNotFoundError, StorageMoveError

        try:
            if not default_storage.exists(source_path):
                raise StorageFileNotFoundError(f"Source file not found: {source_path}")

            # Copy then delete (Django storage doesn't have native move)
            self.copy_file(source_path, destination_path)
            default_storage.delete(source_path)

            return {
                "source_path": source_path,
                "destination_path": destination_path,
            }
        except StorageFileNotFoundError:
            raise
        except Exception as e:
            raise StorageMoveError(f"Failed to move file: {str(e)}") from e

    def delete_files(self, file_paths: list) -> dict[str, Any]:
        """Delete multiple files from storage."""
        deleted = []
        errors = []

        for file_path in file_paths:
            try:
                if default_storage.exists(file_path):
                    default_storage.delete(file_path)
                    deleted.append(file_path)
                else:
                    errors.append({"file_path": file_path, "error": "File not found"})
            except Exception as e:
                errors.append({"file_path": file_path, "error": str(e)})

        return {
            "deleted": deleted,
            "errors": errors,
        }
