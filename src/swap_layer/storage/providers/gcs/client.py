"""
Google Cloud Storage provider implementing StorageProviderAdapter.

Provides a provider-agnostic interface backed by GCS, covering all operations
from the legacy codebase (buckets.py, objects.py, security_audits.py) and
extending with the full StorageProviderAdapter interface.

Authentication:
    Uses Application Default Credentials (ADC) by default. Supports:
    - Service account JSON key file (via credentials_path)
    - GCE metadata server (when running on GCP)
    - GOOGLE_APPLICATION_CREDENTIALS environment variable
    - Workload Identity (GKE)

Usage:
    from swap_layer.storage.providers.gcs import GCSStorageProvider

    # Using ADC (recommended for production)
    provider = GCSStorageProvider(bucket_name='my-bucket')

    # Using service account key file
    provider = GCSStorageProvider(
        bucket_name='my-bucket',
        credentials_path='/path/to/service-account.json',
    )

    # With custom project/location
    provider = GCSStorageProvider(
        bucket_name='my-bucket',
        project_id='my-project',
        location='europe-west1',
    )
"""

import io
import logging
from datetime import timedelta
from typing import Any, BinaryIO, Optional

from ...adapter import (
    StorageCopyError,
    StorageDeleteError,
    StorageDownloadError,
    StorageFileNotFoundError,
    StorageMoveError,
    StorageProviderAdapter,
    StorageUploadError,
)

logger = logging.getLogger(__name__)


def _get_storage_client(credentials_path: Optional[str] = None, project_id: Optional[str] = None):
    """
    Create a GCS client with the given credentials.

    Lazy imports google.cloud.storage to avoid hard dependency at module level.
    """
    from google.cloud import storage

    if credentials_path:
        return storage.Client.from_service_account_json(
            credentials_path, project=project_id
        )
    return storage.Client(project=project_id)


class GCSStorageProvider(StorageProviderAdapter):
    """
    Google Cloud Storage implementation of StorageProviderAdapter.

    Provides all standard CRUD operations plus GCS-specific features like
    signed URLs, upload from string, and download as text/bytes.

    The provider operates on a single default bucket but supports cross-bucket
    operations via explicit bucket_name parameters on extended methods.
    """

    def __init__(
        self,
        bucket_name: str,
        credentials_path: Optional[str] = None,
        project_id: Optional[str] = None,
        location: str = "europe-west1",
        storage_class: str = "STANDARD",
    ):
        """
        Initialize GCS storage provider.

        Args:
            bucket_name: Default GCS bucket name for all operations
            credentials_path: Path to service account JSON key file.
                            If None, uses Application Default Credentials.
            project_id: GCP project ID (optional, inferred from credentials)
            location: Default location for new buckets
            storage_class: Default storage class for new buckets
        """
        self.bucket_name = bucket_name
        self.credentials_path = credentials_path
        self.project_id = project_id
        self.location = location
        self.storage_class = storage_class

        self._client = None

    @property
    def client(self):
        """Lazy-initialize the GCS client."""
        if self._client is None:
            self._client = _get_storage_client(self.credentials_path, self.project_id)
        return self._client

    @property
    def bucket(self):
        """Get the default bucket object."""
        return self.client.bucket(self.bucket_name)

    # ═══════════════════════════════════════════════════════════════════
    # File Operations (StorageProviderAdapter interface)
    # ═══════════════════════════════════════════════════════════════════

    def upload_file(
        self,
        file_path: str,
        file_data: BinaryIO,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
        public: bool = False,
    ) -> dict[str, Any]:
        """
        Upload a file to GCS.

        Handles both file-like objects and raw bytes. Automatically seeks to
        beginning if the file object supports it.

        Args:
            file_path: Object path in the bucket (e.g., 'uploads/images/photo.jpg')
            file_data: Binary file data or file-like object
            content_type: MIME type (e.g., 'image/jpeg'). Auto-detected if None.
            metadata: Custom metadata key-value pairs stored with the object
            public: Whether to grant public read access

        Returns:
            Dict with: url, file_path, size, content_type, etag
        """
        try:
            blob = self.bucket.blob(file_path)

            if metadata:
                blob.metadata = metadata

            # Handle file-like objects with seek support
            if hasattr(file_data, 'seek'):
                file_data.seek(0)

            # Determine upload method based on input type
            if hasattr(file_data, 'read'):
                blob.upload_from_file(
                    file_data,
                    content_type=content_type,
                )
            else:
                blob.upload_from_string(
                    file_data,
                    content_type=content_type or 'application/octet-stream',
                )

            if public:
                blob.make_public()

            # Reload to get metadata
            blob.reload()

            return {
                'url': blob.public_url if public else f"gs://{self.bucket_name}/{file_path}",
                'file_path': file_path,
                'size': blob.size,
                'content_type': blob.content_type,
                'etag': blob.etag,
            }

        except Exception as e:
            raise StorageUploadError(f"Failed to upload '{file_path}' to GCS: {e}") from e

    def download_file(self, file_path: str, destination: str | None = None) -> bytes:
        """
        Download a file from GCS.

        Args:
            file_path: Object path in the bucket
            destination: Optional local file path to save to

        Returns:
            File contents as bytes (if destination not provided)
        """
        try:
            blob = self.bucket.blob(file_path)

            if not blob.exists():
                raise StorageFileNotFoundError(f"File not found: gs://{self.bucket_name}/{file_path}")

            if destination:
                blob.download_to_filename(destination)
                # Still return the bytes for consistency
                with open(destination, 'rb') as f:
                    return f.read()
            else:
                return blob.download_as_bytes()

        except StorageFileNotFoundError:
            raise
        except Exception as e:
            raise StorageDownloadError(f"Failed to download '{file_path}' from GCS: {e}") from e

    def delete_file(self, file_path: str) -> dict[str, Any]:
        """
        Delete a file from GCS.

        Args:
            file_path: Object path in the bucket

        Returns:
            Dict with: deleted (bool), file_path
        """
        try:
            blob = self.bucket.blob(file_path)

            if not blob.exists():
                raise StorageFileNotFoundError(f"File not found: gs://{self.bucket_name}/{file_path}")

            blob.delete()

            return {
                'deleted': True,
                'file_path': file_path,
            }

        except StorageFileNotFoundError:
            raise
        except Exception as e:
            raise StorageDeleteError(f"Failed to delete '{file_path}' from GCS: {e}") from e

    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists in GCS."""
        blob = self.bucket.blob(file_path)
        return blob.exists()

    def get_file_metadata(self, file_path: str) -> dict[str, Any]:
        """
        Get metadata for a file in GCS.

        Returns:
            Dict with: size, content_type, last_modified, etag, metadata,
                       storage_class, crc32c, md5_hash
        """
        blob = self.bucket.blob(file_path)

        if not blob.exists():
            raise StorageFileNotFoundError(f"File not found: gs://{self.bucket_name}/{file_path}")

        blob.reload()

        return {
            'size': blob.size,
            'content_type': blob.content_type,
            'last_modified': blob.updated,
            'created': blob.time_created,
            'etag': blob.etag,
            'metadata': blob.metadata or {},
            'storage_class': blob.storage_class,
            'crc32c': blob.crc32c,
            'md5_hash': blob.md5_hash,
            'generation': blob.generation,
            'metageneration': blob.metageneration,
        }

    def list_files(
        self, prefix: str | None = None, max_results: int = 1000
    ) -> list[dict[str, Any]]:
        """
        List files in GCS bucket.

        Args:
            prefix: Optional prefix to filter (e.g., 'uploads/images/')
            max_results: Maximum number of results

        Returns:
            List of dicts with: file_path, size, last_modified, etag
        """
        blobs = self.client.list_blobs(
            self.bucket_name,
            prefix=prefix,
            max_results=max_results,
        )

        results = []
        for blob in blobs:
            results.append({
                'file_path': blob.name,
                'size': blob.size,
                'last_modified': blob.updated,
                'etag': blob.etag,
                'content_type': blob.content_type,
            })

        return results

    # ═══════════════════════════════════════════════════════════════════
    # URL Generation
    # ═══════════════════════════════════════════════════════════════════

    def get_file_url(
        self, file_path: str, expiration: timedelta | None = None
    ) -> str:
        """
        Get a URL to access a file.

        If expiration is provided, generates a V4 signed URL.
        Otherwise returns the public URL (only works for public objects).

        Args:
            file_path: Object path in the bucket
            expiration: How long the signed URL should be valid (max 7 days)

        Returns:
            Signed URL (if expiration) or public URL
        """
        blob = self.bucket.blob(file_path)

        if not blob.exists():
            raise StorageFileNotFoundError(f"File not found: gs://{self.bucket_name}/{file_path}")

        if expiration:
            return blob.generate_signed_url(
                version="v4",
                expiration=expiration,
                method="GET",
            )
        else:
            return blob.public_url

    def generate_presigned_upload_url(
        self,
        file_path: str,
        content_type: str | None = None,
        expiration: timedelta = timedelta(hours=1),
    ) -> dict[str, Any]:
        """
        Generate a signed URL for direct upload from client.

        Uses GCS V4 signed URLs with PUT method for direct browser uploads.

        Args:
            file_path: Object path for the upload
            content_type: Expected MIME type
            expiration: How long the URL should be valid

        Returns:
            Dict with: url, method ('PUT'), file_path, expiration
        """
        blob = self.bucket.blob(file_path)

        url = blob.generate_signed_url(
            version="v4",
            expiration=expiration,
            method="PUT",
            content_type=content_type,
        )

        return {
            'url': url,
            'method': 'PUT',
            'file_path': file_path,
            'content_type': content_type,
            'expiration_seconds': int(expiration.total_seconds()),
        }

    # ═══════════════════════════════════════════════════════════════════
    # Bulk Operations
    # ═══════════════════════════════════════════════════════════════════

    def copy_file(self, source_path: str, destination_path: str) -> dict[str, Any]:
        """
        Copy a file within GCS (same or cross-bucket).

        Uses GCS server-side copy (no data transfer through client).

        Args:
            source_path: Source object path
            destination_path: Destination object path

        Returns:
            Dict with: source_path, destination_path, etag
        """
        try:
            source_blob = self.bucket.blob(source_path)

            if not source_blob.exists():
                raise StorageFileNotFoundError(
                    f"Source file not found: gs://{self.bucket_name}/{source_path}"
                )

            new_blob = self.bucket.copy_blob(
                source_blob,
                self.bucket,
                new_name=destination_path,
            )

            return {
                'source_path': source_path,
                'destination_path': destination_path,
                'etag': new_blob.etag if new_blob else None,
            }

        except StorageFileNotFoundError:
            raise
        except Exception as e:
            raise StorageCopyError(
                f"Failed to copy '{source_path}' to '{destination_path}': {e}"
            ) from e

    def move_file(self, source_path: str, destination_path: str) -> dict[str, Any]:
        """
        Move/rename a file within GCS.

        Implemented as copy + delete (GCS doesn't have a native move).

        Args:
            source_path: Source object path
            destination_path: Destination object path

        Returns:
            Dict with: source_path, destination_path
        """
        try:
            source_blob = self.bucket.blob(source_path)

            if not source_blob.exists():
                raise StorageFileNotFoundError(
                    f"Source file not found: gs://{self.bucket_name}/{source_path}"
                )

            # Copy then delete
            self.bucket.copy_blob(source_blob, self.bucket, new_name=destination_path)
            source_blob.delete()

            return {
                'source_path': source_path,
                'destination_path': destination_path,
            }

        except StorageFileNotFoundError:
            raise
        except Exception as e:
            raise StorageMoveError(
                f"Failed to move '{source_path}' to '{destination_path}': {e}"
            ) from e

    def delete_files(self, file_paths: list[str]) -> dict[str, Any]:
        """
        Delete multiple files from GCS.

        Attempts to delete all files, collecting errors for any that fail.

        Args:
            file_paths: List of object paths to delete

        Returns:
            Dict with: deleted (list), errors (list)
        """
        deleted = []
        errors = []

        for file_path in file_paths:
            try:
                blob = self.bucket.blob(file_path)
                blob.delete()
                deleted.append(file_path)
            except Exception as e:
                errors.append({
                    'file_path': file_path,
                    'error': str(e),
                })

        return {
            'deleted': deleted,
            'errors': errors,
        }

    # ═══════════════════════════════════════════════════════════════════
    # Extended GCS-specific Operations
    # (Not in StorageProviderAdapter, but needed for legacy compatibility
    #  and available via the provider directly or ScopedStorageProvider)
    # ═══════════════════════════════════════════════════════════════════

    def upload_from_string(
        self,
        file_path: str,
        data: str | bytes,
        content_type: str = "text/plain",
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Upload string/bytes content directly to GCS.

        Replaces legacy patterns:
        - upload_audio_file_to_bucket(bucket, file, dest, content_type)
        - archive_faunadb_document_as_json(bucket, file, dest, content_type)

        Args:
            file_path: Object path in the bucket
            data: String or bytes content to upload
            content_type: MIME type of the content
            metadata: Custom metadata

        Returns:
            Dict with: url, file_path, size, content_type, etag
        """
        try:
            blob = self.bucket.blob(file_path)

            if metadata:
                blob.metadata = metadata

            blob.upload_from_string(data, content_type=content_type)
            blob.reload()

            return {
                'url': f"gs://{self.bucket_name}/{file_path}",
                'file_path': file_path,
                'size': blob.size,
                'content_type': blob.content_type,
                'etag': blob.etag,
            }

        except Exception as e:
            raise StorageUploadError(
                f"Failed to upload string content to '{file_path}': {e}"
            ) from e

    def download_as_bytes(self, file_path: str) -> bytes:
        """
        Download file content as bytes.

        Replaces legacy: convert_file_to_bytes(bucket_name, destination)

        Args:
            file_path: Object path in the bucket

        Returns:
            File content as bytes
        """
        try:
            blob = self.bucket.blob(file_path)

            if not blob.exists():
                raise StorageFileNotFoundError(
                    f"File not found: gs://{self.bucket_name}/{file_path}"
                )

            return blob.download_as_bytes()

        except StorageFileNotFoundError:
            raise
        except Exception as e:
            raise StorageDownloadError(
                f"Failed to download '{file_path}' as bytes: {e}"
            ) from e

    def download_as_text(self, file_path: str, encoding: str = 'utf-8') -> str:
        """
        Download file content as text string.

        Args:
            file_path: Object path in the bucket
            encoding: Text encoding (default: utf-8)

        Returns:
            File content as string
        """
        try:
            blob = self.bucket.blob(file_path)

            if not blob.exists():
                raise StorageFileNotFoundError(
                    f"File not found: gs://{self.bucket_name}/{file_path}"
                )

            return blob.download_as_text(encoding=encoding)

        except StorageFileNotFoundError:
            raise
        except Exception as e:
            raise StorageDownloadError(
                f"Failed to download '{file_path}' as text: {e}"
            ) from e

    def update_metadata(
        self,
        file_path: str,
        metadata: dict[str, str],
        merge: bool = True,
    ) -> dict[str, Any]:
        """
        Update custom metadata on an object.

        Args:
            file_path: Object path in the bucket
            metadata: Metadata key-value pairs to set
            merge: If True, merge with existing metadata. If False, replace.

        Returns:
            Dict with: file_path, metadata (updated)
        """
        blob = self.bucket.blob(file_path)

        if not blob.exists():
            raise StorageFileNotFoundError(
                f"File not found: gs://{self.bucket_name}/{file_path}"
            )

        blob.reload()

        if merge and blob.metadata:
            updated_metadata = {**blob.metadata, **metadata}
        else:
            updated_metadata = metadata

        blob.metadata = updated_metadata
        blob.patch()

        return {
            'file_path': file_path,
            'metadata': updated_metadata,
        }

    # ═══════════════════════════════════════════════════════════════════
    # Bucket Operations
    # ═══════════════════════════════════════════════════════════════════

    def create_bucket(
        self,
        bucket_name: Optional[str] = None,
        location: Optional[str] = None,
        storage_class: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create a new GCS bucket.

        Args:
            bucket_name: Bucket name (defaults to self.bucket_name)
            location: GCP region (defaults to self.location)
            storage_class: Storage class (defaults to self.storage_class)

        Returns:
            Dict with: name, location, storage_class, created
        """
        name = bucket_name or self.bucket_name
        loc = location or self.location
        sc = storage_class or self.storage_class

        bucket = self.client.bucket(name)
        bucket.storage_class = sc

        new_bucket = self.client.create_bucket(bucket, location=loc)

        return {
            'name': new_bucket.name,
            'location': new_bucket.location,
            'storage_class': new_bucket.storage_class,
            'created': new_bucket.time_created,
        }

    def delete_bucket(self, bucket_name: Optional[str] = None, force: bool = False) -> dict[str, Any]:
        """
        Delete a GCS bucket.

        Args:
            bucket_name: Bucket to delete (defaults to self.bucket_name)
            force: If True, delete all objects first

        Returns:
            Dict with: deleted (bool), bucket_name
        """
        name = bucket_name or self.bucket_name
        bucket = self.client.get_bucket(name)

        if force:
            # Delete all blobs first
            blobs = list(bucket.list_blobs())
            bucket.delete_blobs(blobs)

        bucket.delete()

        return {
            'deleted': True,
            'bucket_name': name,
        }

    def bucket_exists(self, bucket_name: Optional[str] = None) -> bool:
        """Check if a bucket exists."""
        name = bucket_name or self.bucket_name
        bucket = self.client.bucket(name)
        return bucket.exists()

    def get_bucket_metadata(self, bucket_name: Optional[str] = None) -> dict[str, Any]:
        """
        Get bucket metadata.

        Returns:
            Dict with: name, location, storage_class, created, versioning, labels
        """
        name = bucket_name or self.bucket_name
        bucket = self.client.get_bucket(name)

        return {
            'name': bucket.name,
            'location': bucket.location,
            'storage_class': bucket.storage_class,
            'created': bucket.time_created,
            'versioning_enabled': bucket.versioning_enabled,
            'labels': bucket.labels or {},
        }
