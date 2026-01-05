from typing import Dict, Any, Optional, List, BinaryIO
from datetime import timedelta
from ...adapter import (
    StorageProviderAdapter,
    StorageUploadError,
    StorageCopyError,
)


class S3StorageProvider(StorageProviderAdapter):
    """
    AWS S3 storage provider.
    
    To complete this implementation:
    1. Install boto3: pip install boto3
    2. Configure AWS credentials in settings or environment
    3. Implement all abstract methods using boto3 client
    
    Configuration needed in settings.py:
        AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
        AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
        AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
        AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
    """

    def __init__(self):
        """Initialize S3 storage provider."""
        try:
            from django.conf import settings
            import boto3
            
            aws_access_key_id = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
            aws_secret_access_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
            aws_region_name = getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1')
            
            if not aws_access_key_id or not aws_secret_access_key:
                raise ValueError("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be configured")
            
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=aws_region_name
            )
            self.bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
            
            if not self.bucket_name:
                raise ValueError("AWS_STORAGE_BUCKET_NAME must be configured")
            
        except ImportError:
            raise ImportError("boto3 library not installed. Run: pip install boto3")

    def upload_file(
        self,
        file_path: str,
        file_data: BinaryIO,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        public: bool = False
    ) -> Dict[str, Any]:
        """Upload a file to S3."""
        try:
            # Prepare upload parameters
            extra_args = {}
            
            if content_type:
                extra_args['ContentType'] = content_type
            
            if metadata:
                extra_args['Metadata'] = metadata
            
            if public:
                extra_args['ACL'] = 'public-read'
            
            # Upload the file
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_path,
                Body=file_data,
                **extra_args
            )
            
            # Get file metadata
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            
            # Generate URL
            if public:
                url = f"https://{self.bucket_name}.s3.amazonaws.com/{file_path}"
            else:
                url = self.get_file_url(file_path)
            
            return {
                'url': url,
                'file_path': file_path,
                'size': response.get('ContentLength', 0),
                'content_type': response.get('ContentType', content_type or 'application/octet-stream'),
                'etag': response.get('ETag', '').strip('"'),
            }
        except Exception as e:
            raise StorageUploadError(f"Failed to upload file to S3: {str(e)}")

    def download_file(
        self,
        file_path: str,
        destination: Optional[str] = None
    ) -> bytes:
        """Download a file from S3."""
        from infrastructure.storage.adapter import StorageFileNotFoundError, StorageDownloadError
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            
            file_content = response['Body'].read()
            
            if destination:
                with open(destination, 'wb') as f:
                    f.write(file_content)
                return b''
            else:
                return file_content
                
        except self.s3_client.exceptions.NoSuchKey:
            raise StorageFileNotFoundError(f"File not found in S3: {file_path}")
        except Exception as e:
            raise StorageDownloadError(f"Failed to download file from S3: {str(e)}")

    def delete_file(self, file_path: str) -> Dict[str, Any]:
        """Delete a file from S3."""
        from infrastructure.storage.adapter import StorageFileNotFoundError, StorageDeleteError
        
        try:
            # Check if file exists first
            if not self.file_exists(file_path):
                raise StorageFileNotFoundError(f"File not found in S3: {file_path}")
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            
            return {
                'deleted': True,
                'file_path': file_path,
            }
        except StorageFileNotFoundError:
            raise
        except Exception as e:
            raise StorageDeleteError(f"Failed to delete file from S3: {str(e)}")

    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists in S3."""
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            return True
        except self.s3_client.exceptions.NoSuchKey:
            return False
        except Exception:
            return False

    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Get metadata for a file in S3."""
        from infrastructure.storage.adapter import StorageFileNotFoundError
        from datetime import datetime
        
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            
            return {
                'size': response.get('ContentLength', 0),
                'content_type': response.get('ContentType', 'application/octet-stream'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag', '').strip('"'),
                'metadata': response.get('Metadata', {}),
            }
        except self.s3_client.exceptions.NoSuchKey:
            raise StorageFileNotFoundError(f"File not found in S3: {file_path}")
        except Exception as e:
            raise StorageFileNotFoundError(f"Failed to get file metadata from S3: {str(e)}")

    def list_files(
        self,
        prefix: Optional[str] = None,
        max_results: int = 1000
    ) -> List[Dict[str, Any]]:
        """List files in S3."""
        try:
            params = {
                'Bucket': self.bucket_name,
                'MaxKeys': max_results
            }
            
            if prefix:
                params['Prefix'] = prefix
            
            response = self.s3_client.list_objects_v2(**params)
            
            results = []
            for obj in response.get('Contents', []):
                results.append({
                    'file_path': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag'].strip('"'),
                })
            
            return results
        except Exception as e:
            return []

    def get_file_url(
        self,
        file_path: str,
        expiration: Optional[timedelta] = None
    ) -> str:
        """Get a URL to access a file in S3."""
        try:
            if expiration:
                # Generate presigned URL for private files
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self.bucket_name,
                        'Key': file_path
                    },
                    ExpiresIn=int(expiration.total_seconds())
                )
            else:
                # Return public URL (assumes file is public)
                url = f"https://{self.bucket_name}.s3.amazonaws.com/{file_path}"
            
            return url
        except Exception as e:
            raise StorageUploadError(f"Failed to generate file URL: {str(e)}")

    def generate_presigned_upload_url(
        self,
        file_path: str,
        content_type: Optional[str] = None,
        expiration: timedelta = timedelta(hours=1)
    ) -> Dict[str, Any]:
        """Generate a presigned URL for direct upload to S3."""
        try:
            conditions = []
            fields = {}
            
            if content_type:
                conditions.append(['eq', '$Content-Type', content_type])
                fields['Content-Type'] = content_type
            
            # Generate presigned POST
            response = self.s3_client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=file_path,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=int(expiration.total_seconds())
            )
            
            return {
                'url': response['url'],
                'fields': response['fields'],
                'method': 'POST',
            }
        except Exception as e:
            raise StorageUploadError(f"Failed to generate presigned upload URL: {str(e)}")

    def copy_file(
        self,
        source_path: str,
        destination_path: str
    ) -> Dict[str, Any]:
        """Copy a file within S3."""
        from infrastructure.storage.adapter import StorageFileNotFoundError, StorageCopyError
        
        try:
            # Check if source file exists
            if not self.file_exists(source_path):
                raise StorageFileNotFoundError(f"Source file not found in S3: {source_path}")
            
            # Copy the object
            copy_source = {
                'Bucket': self.bucket_name,
                'Key': source_path
            }
            
            response = self.s3_client.copy_object(
                Bucket=self.bucket_name,
                CopySource=copy_source,
                Key=destination_path
            )
            
            return {
                'source_path': source_path,
                'destination_path': destination_path,
                'etag': response.get('CopyObjectResult', {}).get('ETag', '').strip('"'),
            }
        except StorageFileNotFoundError:
            raise
        except Exception as e:
            raise StorageCopyError(f"Failed to copy file in S3: {str(e)}")

    def move_file(
        self,
        source_path: str,
        destination_path: str
    ) -> Dict[str, Any]:
        """Move/rename a file within S3."""
        from infrastructure.storage.adapter import StorageFileNotFoundError, StorageMoveError
        
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
            raise StorageMoveError(f"Failed to move file in S3: {str(e)}")
        except Exception as e:
            raise StorageMoveError(f"Failed to move file in S3: {str(e)}")

    def delete_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """Delete multiple files from S3."""
        try:
            deleted = []
            errors = []
            
            # S3 supports batch delete up to 1000 objects
            if len(file_paths) <= 1000:
                # Use batch delete
                objects = [{'Key': path} for path in file_paths]
                
                response = self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': objects}
                )
                
                # Track successful deletions
                for obj in response.get('Deleted', []):
                    deleted.append(obj['Key'])
                
                # Track errors
                for error in response.get('Errors', []):
                    errors.append({
                        'file_path': error['Key'],
                        'error': error.get('Message', 'Unknown error'),
                    })
            else:
                # Delete individually for large batches
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
