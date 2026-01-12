from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any, BinaryIO


class StorageProviderAdapter(ABC):
    """
    Abstract base class for Storage Providers (S3, Azure Blob, Google Cloud Storage, local filesystem, etc.)
    This ensures we can switch providers without rewriting the application logic.
    """

    # File Operations
    @abstractmethod
    def upload_file(
        self,
        file_path: str,
        file_data: BinaryIO,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
        public: bool = False,
    ) -> dict[str, Any]:
        """
        Upload a file to storage.

        Args:
            file_path: Path/key for the file in storage (e.g., 'uploads/images/photo.jpg')
            file_data: Binary file data or file-like object
            content_type: MIME type of the file (e.g., 'image/jpeg')
            metadata: Custom metadata key-value pairs
            public: Whether the file should be publicly accessible

        Returns:
            Dict with keys: url, file_path, size, content_type, etag

        Raises:
            StorageUploadError: If upload fails
        """
        pass

    @abstractmethod
    def download_file(self, file_path: str, destination: str | None = None) -> bytes:
        """
        Download a file from storage.

        Args:
            file_path: Path/key of the file in storage
            destination: Optional local file path to save to

        Returns:
            File contents as bytes (if destination not provided)

        Raises:
            StorageFileNotFoundError: If file doesn't exist
            StorageDownloadError: If download fails
        """
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> dict[str, Any]:
        """
        Delete a file from storage.

        Args:
            file_path: Path/key of the file in storage

        Returns:
            Dict with keys: deleted, file_path

        Raises:
            StorageFileNotFoundError: If file doesn't exist
            StorageDeleteError: If deletion fails
        """
        pass

    @abstractmethod
    def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists in storage.

        Args:
            file_path: Path/key of the file in storage

        Returns:
            True if file exists, False otherwise
        """
        pass

    @abstractmethod
    def get_file_metadata(self, file_path: str) -> dict[str, Any]:
        """
        Get metadata for a file.

        Args:
            file_path: Path/key of the file in storage

        Returns:
            Dict with keys: size, content_type, last_modified, etag, metadata

        Raises:
            StorageFileNotFoundError: If file doesn't exist
        """
        pass

    @abstractmethod
    def list_files(
        self, prefix: str | None = None, max_results: int = 1000
    ) -> list[dict[str, Any]]:
        """
        List files in storage.

        Args:
            prefix: Optional prefix to filter files (e.g., 'uploads/images/')
            max_results: Maximum number of results to return

        Returns:
            List of dicts with keys: file_path, size, last_modified, etag
        """
        pass

    # URL Generation
    @abstractmethod
    def get_file_url(self, file_path: str, expiration: timedelta | None = None) -> str:
        """
        Get a URL to access a file.

        Args:
            file_path: Path/key of the file in storage
            expiration: Optional expiration time for signed URLs (for private files)

        Returns:
            URL to access the file (signed URL if private, direct URL if public)

        Raises:
            StorageFileNotFoundError: If file doesn't exist
        """
        pass

    @abstractmethod
    def generate_presigned_upload_url(
        self,
        file_path: str,
        content_type: str | None = None,
        expiration: timedelta = timedelta(hours=1),
    ) -> dict[str, Any]:
        """
        Generate a presigned URL for direct upload from client.

        Args:
            file_path: Path/key for the file in storage
            content_type: Expected MIME type
            expiration: How long the URL should be valid

        Returns:
            Dict with keys: url, fields (for POST uploads), method (PUT or POST)
        """
        pass

    # Bulk Operations
    @abstractmethod
    def copy_file(self, source_path: str, destination_path: str) -> dict[str, Any]:
        """
        Copy a file within storage.

        Args:
            source_path: Path/key of source file
            destination_path: Path/key of destination file

        Returns:
            Dict with keys: source_path, destination_path, etag

        Raises:
            StorageFileNotFoundError: If source file doesn't exist
            StorageCopyError: If copy fails
        """
        pass

    @abstractmethod
    def move_file(self, source_path: str, destination_path: str) -> dict[str, Any]:
        """
        Move/rename a file within storage.

        Args:
            source_path: Path/key of source file
            destination_path: Path/key of destination file

        Returns:
            Dict with keys: source_path, destination_path

        Raises:
            StorageFileNotFoundError: If source file doesn't exist
            StorageMoveError: If move fails
        """
        pass

    @abstractmethod
    def delete_files(self, file_paths: list[str]) -> dict[str, Any]:
        """
        Delete multiple files from storage.

        Args:
            file_paths: List of file paths/keys to delete

        Returns:
            Dict with keys: deleted (list of deleted paths), errors (list of errors)
        """
        pass


# Custom Exceptions
class StorageError(Exception):
    """Base exception for storage operations."""

    pass


class StorageUploadError(StorageError):
    """Raised when file upload fails."""

    pass


class StorageDownloadError(StorageError):
    """Raised when file download fails."""

    pass


class StorageFileNotFoundError(StorageError):
    """Raised when a file is not found."""

    pass


class StorageDeleteError(StorageError):
    """Raised when file deletion fails."""

    pass


class StorageCopyError(StorageError):
    """Raised when file copy fails."""

    pass


class StorageMoveError(StorageError):
    """Raised when file move fails."""

    pass
