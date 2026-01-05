from typing import Dict, Any, Optional, List, BinaryIO
from datetime import timedelta
from ...adapter import (
    StorageProviderAdapter,
    StorageUploadError,
    StorageCopyError,
    StorageMoveError,
)


class AzureBlobStorageProvider(StorageProviderAdapter):
    """
    Azure Blob Storage provider.
    
    To complete this implementation:
    1. Install azure-storage-blob: pip install azure-storage-blob
    2. Configure Azure credentials in settings or environment
    3. Implement all abstract methods using BlobServiceClient
    
    Configuration needed in settings.py:
        AZURE_STORAGE_CONNECTION_STRING = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
        AZURE_STORAGE_CONTAINER_NAME = os.environ.get('AZURE_STORAGE_CONTAINER_NAME')
    """

    def __init__(self):
        """Initialize Azure Blob storage provider."""
        try:
            from django.conf import settings
            from azure.storage.blob import BlobServiceClient
            
            connection_string = getattr(settings, 'AZURE_STORAGE_CONNECTION_STRING', None)
            
            if not connection_string:
                raise ValueError("AZURE_STORAGE_CONNECTION_STRING must be configured")
            
            self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            self.container_name = getattr(settings, 'AZURE_STORAGE_CONTAINER_NAME', None)
            
            if not self.container_name:
                raise ValueError("AZURE_STORAGE_CONTAINER_NAME must be configured")
            
            self.container_client = self.blob_service_client.get_container_client(self.container_name)
            
        except ImportError:
            raise ImportError("azure-storage-blob library not installed. Run: pip install azure-storage-blob")

    def upload_file(
        self,
        file_path: str,
        file_data: BinaryIO,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        public: bool = False
    ) -> Dict[str, Any]:
        """Upload a file to Azure Blob Storage."""
        try:
            blob_client = self.container_client.get_blob_client(file_path)
            
            # Prepare content settings
            content_settings = None
            if content_type:
                from azure.storage.blob import ContentSettings
                content_settings = ContentSettings(content_type=content_type)
            
            # Upload the blob
            blob_client.upload_blob(
                file_data,
                overwrite=True,
                content_settings=content_settings,
                metadata=metadata
            )
            
            # Get blob properties
            properties = blob_client.get_blob_properties()
            
            return {
                'url': blob_client.url,
                'file_path': file_path,
                'size': properties.size,
                'content_type': properties.content_settings.content_type if properties.content_settings else 'application/octet-stream',
                'etag': properties.etag.strip('"'),
            }
        except Exception as e:
            raise StorageUploadError(f"Failed to upload file to Azure: {str(e)}")

    def download_file(
        self,
        file_path: str,
        destination: Optional[str] = None
    ) -> bytes:
        """Download a file from Azure Blob Storage."""
        from storage.adapter import StorageFileNotFoundError, StorageDownloadError
        
        try:
            blob_client = self.container_client.get_blob_client(file_path)
            
            download_stream = blob_client.download_blob()
            file_content = download_stream.readall()
            
            if destination:
                with open(destination, 'wb') as f:
                    f.write(file_content)
                return b''
            else:
                return file_content
                
        except Exception as e:
            if 'not found' in str(e).lower() or 'BlobNotFound' in str(e):
                raise StorageFileNotFoundError(f"File not found in Azure: {file_path}")
            raise StorageDownloadError(f"Failed to download file from Azure: {str(e)}")

    def delete_file(self, file_path: str) -> Dict[str, Any]:
        """Delete a file from Azure Blob Storage."""
        from storage.adapter import StorageFileNotFoundError, StorageDeleteError
        
        try:
            blob_client = self.container_client.get_blob_client(file_path)
            
            # Check if file exists first
            if not self.file_exists(file_path):
                raise StorageFileNotFoundError(f"File not found in Azure: {file_path}")
            
            blob_client.delete_blob()
            
            return {
                'deleted': True,
                'file_path': file_path,
            }
        except StorageFileNotFoundError:
            raise
        except Exception as e:
            raise StorageDeleteError(f"Failed to delete file from Azure: {str(e)}")

    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists in Azure Blob Storage."""
        try:
            blob_client = self.container_client.get_blob_client(file_path)
            return blob_client.exists()
        except Exception:
            return False

    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Get metadata for a file in Azure Blob Storage."""
        from storage.adapter import StorageFileNotFoundError
        
        try:
            blob_client = self.container_client.get_blob_client(file_path)
            properties = blob_client.get_blob_properties()
            
            return {
                'size': properties.size,
                'content_type': properties.content_settings.content_type if properties.content_settings else 'application/octet-stream',
                'last_modified': properties.last_modified,
                'etag': properties.etag.strip('"'),
                'metadata': properties.metadata or {},
            }
        except Exception as e:
            if 'not found' in str(e).lower() or 'BlobNotFound' in str(e):
                raise StorageFileNotFoundError(f"File not found in Azure: {file_path}")
            raise StorageFileNotFoundError(f"Failed to get file metadata from Azure: {str(e)}")

    def list_files(
        self,
        prefix: Optional[str] = None,
        max_results: int = 1000
    ) -> List[Dict[str, Any]]:
        """List files in Azure Blob Storage."""
        try:
            params = {}
            if prefix:
                params['name_starts_with'] = prefix
            
            blobs = self.container_client.list_blobs(**params)
            
            results = []
            for blob in blobs:
                results.append({
                    'file_path': blob.name,
                    'size': blob.size,
                    'last_modified': blob.last_modified,
                    'etag': blob.etag.strip('"'),
                })
                
                if len(results) >= max_results:
                    break
            
            return results
        except Exception as e:
            return []

    def get_file_url(
        self,
        file_path: str,
        expiration: Optional[timedelta] = None
    ) -> str:
        """Get a URL to access a file in Azure Blob Storage."""
        try:
            blob_client = self.container_client.get_blob_client(file_path)
            
            if expiration:
                # Generate SAS URL for temporary access
                from azure.storage.blob import generate_blob_sas, BlobSasPermissions
                from datetime import datetime, timezone
                from django.conf import settings
                
                # Get account key from connection string
                connection_string = getattr(settings, 'AZURE_STORAGE_CONNECTION_STRING', '')
                account_name = None
                account_key = None
                
                for part in connection_string.split(';'):
                    if part.startswith('AccountName='):
                        account_name = part.split('=', 1)[1]
                    elif part.startswith('AccountKey='):
                        account_key = part.split('=', 1)[1]
                
                if not account_name or not account_key:
                    raise ValueError("Could not parse account credentials from connection string")
                
                sas_token = generate_blob_sas(
                    account_name=account_name,
                    container_name=self.container_name,
                    blob_name=file_path,
                    account_key=account_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=datetime.now(timezone.utc) + expiration
                )
                
                return f"{blob_client.url}?{sas_token}"
            else:
                # Return public URL
                return blob_client.url
                
        except Exception as e:
            raise StorageUploadError(f"Failed to generate file URL: {str(e)}")

    def generate_presigned_upload_url(
        self,
        file_path: str,
        content_type: Optional[str] = None,
        expiration: timedelta = timedelta(hours=1)
    ) -> Dict[str, Any]:
        """Generate a presigned URL for direct upload to Azure Blob Storage."""
        try:
            from azure.storage.blob import generate_blob_sas, BlobSasPermissions
            from datetime import datetime, timezone
            from django.conf import settings
            
            blob_client = self.container_client.get_blob_client(file_path)
            
            # Get account credentials from connection string
            connection_string = getattr(settings, 'AZURE_STORAGE_CONNECTION_STRING', '')
            account_name = None
            account_key = None
            
            for part in connection_string.split(';'):
                if part.startswith('AccountName='):
                    account_name = part.split('=', 1)[1]
                elif part.startswith('AccountKey='):
                    account_key = part.split('=', 1)[1]
            
            if not account_name or not account_key:
                raise ValueError("Could not parse account credentials from connection string")
            
            # Generate SAS token with write permissions
            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=self.container_name,
                blob_name=file_path,
                account_key=account_key,
                permission=BlobSasPermissions(write=True, create=True),
                expiry=datetime.now(timezone.utc) + expiration
            )
            
            url = f"{blob_client.url}?{sas_token}"
            
            return {
                'url': url,
                'fields': {'x-ms-blob-type': 'BlockBlob'},
                'method': 'PUT',
            }
        except Exception as e:
            raise StorageUploadError(f"Failed to generate presigned upload URL: {str(e)}")

    def copy_file(
        self,
        source_path: str,
        destination_path: str
    ) -> Dict[str, Any]:
        """Copy a file within Azure Blob Storage."""
        from storage.adapter import StorageFileNotFoundError, StorageCopyError
        
        try:
            # Check if source file exists
            if not self.file_exists(source_path):
                raise StorageFileNotFoundError(f"Source file not found in Azure: {source_path}")
            
            source_blob = self.container_client.get_blob_client(source_path)
            dest_blob = self.container_client.get_blob_client(destination_path)
            
            # Start copy operation
            dest_blob.start_copy_from_url(source_blob.url)
            
            # Get destination blob properties
            properties = dest_blob.get_blob_properties()
            
            return {
                'source_path': source_path,
                'destination_path': destination_path,
                'etag': properties.etag.strip('"'),
            }
        except StorageFileNotFoundError:
            raise
        except Exception as e:
            raise StorageCopyError(f"Failed to copy file in Azure: {str(e)}")

    def move_file(
        self,
        source_path: str,
        destination_path: str
    ) -> Dict[str, Any]:
        """Move/rename a file within Azure Blob Storage."""
        from storage.adapter import StorageFileNotFoundError, StorageMoveError, StorageCopyError
        
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
            raise StorageMoveError(f"Failed to move file in Azure: {str(e)}")
        except Exception as e:
            raise StorageMoveError(f"Failed to move file in Azure: {str(e)}")

    def delete_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """Delete multiple files from Azure Blob Storage."""
        try:
            deleted = []
            errors = []
            
            # Azure supports batch delete
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
