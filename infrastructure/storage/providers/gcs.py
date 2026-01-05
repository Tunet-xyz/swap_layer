from typing import Dict, Any, Optional, List, BinaryIO
from datetime import timedelta
from infrastructure.storage.adapter import (
    StorageProviderAdapter,
    StorageUploadError,
    StorageDownloadError,
    StorageFileNotFoundError,
    StorageDeleteError,
    StorageCopyError,
    StorageMoveError,
)


class GCSStorageProvider(StorageProviderAdapter):
    """
    Google Cloud Storage provider.
    
    To complete this implementation:
    1. Install google-cloud-storage: pip install google-cloud-storage
    2. Configure GCP credentials in settings or environment
    3. Implement all abstract methods using GCS client
    
    Configuration needed in settings.py:
        GCS_PROJECT_ID = os.environ.get('GCS_PROJECT_ID')
        GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME')
        GCS_CREDENTIALS_PATH = os.environ.get('GCS_CREDENTIALS_PATH')  # Optional, uses default credentials if not set
    """

    def __init__(self):
        """Initialize GCS storage provider."""
        try:
            from django.conf import settings
            from google.cloud import storage
            
            project_id = getattr(settings, 'GCS_PROJECT_ID', None)
            credentials_path = getattr(settings, 'GCS_CREDENTIALS_PATH', None)
            
            if not project_id:
                raise ValueError("GCS_PROJECT_ID must be configured")
            
            # Initialize client with credentials if provided
            if credentials_path:
                self.storage_client = storage.Client.from_service_account_json(
                    credentials_path,
                    project=project_id
                )
            else:
                # Use default credentials (from GOOGLE_APPLICATION_CREDENTIALS env var)
                self.storage_client = storage.Client(project=project_id)
            
            self.bucket_name = getattr(settings, 'GCS_BUCKET_NAME', None)
            
            if not self.bucket_name:
                raise ValueError("GCS_BUCKET_NAME must be configured")
            
            self.bucket = self.storage_client.bucket(self.bucket_name)
            
        except ImportError:
            raise ImportError("google-cloud-storage library not installed. Run: pip install google-cloud-storage")

    def upload_file(
        self,
        file_path: str,
        file_data: BinaryIO,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        public: bool = False
    ) -> Dict[str, Any]:
        """Upload a file to GCS."""
        try:
            blob = self.bucket.blob(file_path)
            
            # Set content type if provided
            if content_type:
                blob.content_type = content_type
            
            # Set custom metadata if provided
            if metadata:
                blob.metadata = metadata
            
            # Upload the file
            blob.upload_from_file(file_data, rewind=True)
            
            # Make public if requested
            if public:
                blob.make_public()
            
            # Reload to get updated properties
            blob.reload()
            
            return {
                'url': blob.public_url if public else blob.public_url,
                'file_path': file_path,
                'size': blob.size,
                'content_type': blob.content_type or 'application/octet-stream',
                'etag': blob.etag,
            }
        except Exception as e:
            raise StorageUploadError(f"Failed to upload file to GCS: {str(e)}")

    def download_file(
        self,
        file_path: str,
        destination: Optional[str] = None
    ) -> bytes:
        """Download a file from GCS."""
        try:
            blob = self.bucket.blob(file_path)
            
            if not blob.exists():
                raise StorageFileNotFoundError(f"File not found in GCS: {file_path}")
            
            if destination:
                blob.download_to_filename(destination)
                return b''
            else:
                return blob.download_as_bytes()
                
        except StorageFileNotFoundError:
            raise
        except Exception as e:
            raise StorageDownloadError(f"Failed to download file from GCS: {str(e)}")

    def delete_file(self, file_path: str) -> Dict[str, Any]:
        """Delete a file from GCS."""
        try:
            blob = self.bucket.blob(file_path)
            
            if not blob.exists():
                raise StorageFileNotFoundError(f"File not found in GCS: {file_path}")
            
            blob.delete()
            
            return {
                'deleted': True,
                'file_path': file_path,
            }
        except StorageFileNotFoundError:
            raise
        except Exception as e:
            raise StorageDeleteError(f"Failed to delete file from GCS: {str(e)}")

    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists in GCS."""
        try:
            blob = self.bucket.blob(file_path)
            return blob.exists()
        except Exception:
            return False

    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Get metadata for a file in GCS."""
        try:
            blob = self.bucket.blob(file_path)
            
            if not blob.exists():
                raise StorageFileNotFoundError(f"File not found in GCS: {file_path}")
            
            # Reload to get current properties
            blob.reload()
            
            return {
                'size': blob.size,
                'content_type': blob.content_type or 'application/octet-stream',
                'last_modified': blob.updated,
                'etag': blob.etag,
                'metadata': blob.metadata or {},
            }
        except StorageFileNotFoundError:
            raise
        except Exception as e:
            # General metadata retrieval error
            raise StorageDownloadError(f"Failed to get file metadata from GCS: {str(e)}")

    def list_files(
        self,
        prefix: Optional[str] = None,
        max_results: int = 1000
    ) -> List[Dict[str, Any]]:
        """List files in GCS."""
        try:
            blobs = self.bucket.list_blobs(
                prefix=prefix,
                max_results=max_results
            )
            
            results = []
            for blob in blobs:
                results.append({
                    'file_path': blob.name,
                    'size': blob.size,
                    'last_modified': blob.updated,
                    'etag': blob.etag,
                })
            
            return results
        except Exception as e:
            return []

    def get_file_url(
        self,
        file_path: str,
        expiration: Optional[timedelta] = None
    ) -> str:
        """Get a URL to access a file in GCS."""
        try:
            blob = self.bucket.blob(file_path)
            
            if expiration:
                # Generate signed URL for temporary access
                url = blob.generate_signed_url(
                    version='v4',
                    expiration=expiration,
                    method='GET'
                )
            else:
                # Return public URL
                url = blob.public_url
            
            return url
        except Exception as e:
            raise StorageDownloadError(f"Failed to generate file URL: {str(e)}")

    def generate_presigned_upload_url(
        self,
        file_path: str,
        content_type: Optional[str] = None,
        expiration: timedelta = timedelta(hours=1)
    ) -> Dict[str, Any]:
        """Generate a presigned URL for direct upload to GCS."""
        try:
            blob = self.bucket.blob(file_path)
            
            # Set content type if provided
            if content_type:
                blob.content_type = content_type
            
            # Generate signed URL for PUT upload
            url = blob.generate_signed_url(
                version='v4',
                expiration=expiration,
                method='PUT',
                content_type=content_type
            )
            
            fields = {}
            if content_type:
                fields['Content-Type'] = content_type
            
            return {
                'url': url,
                'fields': fields,
                'method': 'PUT',
            }
        except Exception as e:
            raise StorageUploadError(f"Failed to generate presigned upload URL: {str(e)}")

    def copy_file(
        self,
        source_path: str,
        destination_path: str
    ) -> Dict[str, Any]:
        """Copy a file within GCS."""
        try:
            source_blob = self.bucket.blob(source_path)
            
            if not source_blob.exists():
                raise StorageFileNotFoundError(f"Source file not found in GCS: {source_path}")
            
            # Copy the blob
            destination_blob = self.bucket.copy_blob(
                source_blob,
                self.bucket,
                destination_path
            )
            
            return {
                'source_path': source_path,
                'destination_path': destination_path,
                'etag': destination_blob.etag,
            }
        except StorageFileNotFoundError:
            raise
        except Exception as e:
            raise StorageCopyError(f"Failed to copy file in GCS: {str(e)}")

    def move_file(
        self,
        source_path: str,
        destination_path: str
    ) -> Dict[str, Any]:
        """Move/rename a file within GCS."""
        try:
            # Copy the file first
            self.copy_file(source_path, destination_path)
            
            # Delete the source file
            self.delete_file(source_path)
            
            return {
                'source_path': source_path,
                'destination_path': destination_path,
            }
        except (StorageFileNotFoundError, StorageCopyError) as e:
            raise StorageMoveError(f"Failed to move file in GCS: {str(e)}")
        except Exception as e:
            raise StorageMoveError(f"Failed to move file in GCS: {str(e)}")

    def delete_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """Delete multiple files from GCS."""
        try:
            deleted = []
            errors = []
            
            # GCS doesn't have batch delete, so delete individually
            for file_path in file_paths:
                try:
                    self.delete_file(file_path)
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
        except Exception as e:
            return {
                'deleted': [],
                'errors': [{'error': f'Batch delete failed: {str(e)}'}],
            }
