# Storage Abstraction Layer

A provider-agnostic storage abstraction layer for managing file storage in Django applications. Switch between local filesystem, AWS S3, Azure Blob Storage, and other providers without changing your application code.

## Overview

This abstraction layer follows the same architectural pattern as the authentication, payment, and email abstractions in this project. It provides a consistent interface for file storage operations regardless of the underlying provider.

## Architecture

```
┌─────────────────────────────────────┐
│     Application / Business Logic    │
├─────────────────────────────────────┤
│      Storage Abstraction Layer      │
│    - StorageProviderAdapter (ABC)   │
│    - Factory Function               │
├─────────────────────────────────────┤
│         Provider Implementations     │
│    - LocalFileStorageProvider       │
│    - S3StorageProvider (stub)       │
│    - AzureBlobStorageProvider (stub)│
└─────────────────────────────────────┘
```

## Features

The abstraction provides these operations:

### File Operations
- **upload_file** - Upload files with metadata and access control
- **download_file** - Download files to memory or disk
- **delete_file** - Delete individual files
- **delete_files** - Bulk delete operations
- **file_exists** - Check if a file exists
- **get_file_metadata** - Get file size, type, modification date
- **list_files** - List files with prefix filtering

### File Management
- **copy_file** - Copy files within storage
- **move_file** - Move/rename files
- **get_file_url** - Generate access URLs (signed for private files)
- **generate_presigned_upload_url** - Allow direct client uploads

## Installation

1. Add to `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    # ...
    'swap_layer.storage.apps.StorageConfig',
    # ...
]
```

2. Configure your storage provider in `settings.py`:

```python
# Storage Provider Selection
STORAGE_PROVIDER = 'local'  # 'local', 's3', 'azure', 'django'

# Local Storage Configuration (default)
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# AWS S3 Configuration (if using S3)
AWS_ACCESS_KEY_ID = 'AKIA...'
AWS_SECRET_ACCESS_KEY = '...'
AWS_STORAGE_BUCKET_NAME = 'my-bucket'
AWS_S3_REGION_NAME = 'us-east-1'

# Azure Blob Storage Configuration (if using Azure)
AZURE_STORAGE_CONNECTION_STRING = 'DefaultEndpointsProtocol=https;...'
AZURE_STORAGE_CONTAINER_NAME = 'my-container'
```

**Security:** Use environment variables in production:

```python
import os
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
```

## Usage

### Basic Usage

```python
from swap_layer.storage.factory import get_storage_provider

# Get the configured provider
storage = get_storage_provider()

# Upload a file
with open('photo.jpg', 'rb') as f:
    result = storage.upload_file(
        file_path='uploads/photos/photo.jpg',
        file_data=f,
        content_type='image/jpeg',
        metadata={'user_id': '123'},
        public=True
    )
    print(f"File uploaded: {result['url']}")

# Download a file
file_content = storage.download_file('uploads/photos/photo.jpg')

# Check if file exists
if storage.file_exists('uploads/photos/photo.jpg'):
    print("File exists!")

# Get file metadata
metadata = storage.get_file_metadata('uploads/photos/photo.jpg')
print(f"Size: {metadata['size']} bytes")
print(f"Modified: {metadata['last_modified']}")

# Delete a file
storage.delete_file('uploads/photos/photo.jpg')
```

### Django File Uploads

```python
from django.views import View
from django.http import JsonResponse
from swap_layer.storage.factory import get_storage_provider

class FileUploadView(View):
    def post(self, request):
        storage = get_storage_provider()
        
        # Get uploaded file from request
        uploaded_file = request.FILES['file']
        
        # Upload to storage
        result = storage.upload_file(
            file_path=f'uploads/{request.user.id}/{uploaded_file.name}',
            file_data=uploaded_file,
            content_type=uploaded_file.content_type,
            metadata={
                'user_id': str(request.user.id),
                'original_name': uploaded_file.name,
            },
            public=False
        )
        
        return JsonResponse({
            'url': result['url'],
            'size': result['size'],
        })
```

### Presigned Upload URLs (for S3/Azure)

```python
from swap_layer.storage.factory import get_storage_provider
from datetime import timedelta

storage = get_storage_provider()

# Generate presigned URL for direct client upload
presigned = storage.generate_presigned_upload_url(
    file_path='uploads/photos/new-photo.jpg',
    content_type='image/jpeg',
    expiration=timedelta(minutes=15)
)

# Return to client for direct upload
return JsonResponse({
    'upload_url': presigned['url'],
    'fields': presigned['fields'],
    'method': presigned['method'],
})
```

### List and Filter Files

```python
from swap_layer.storage.factory import get_storage_provider

storage = get_storage_provider()

# List all files in a directory
files = storage.list_files(
    prefix='uploads/photos/',
    max_results=100
)

for file in files:
    print(f"{file['file_path']}: {file['size']} bytes")
```

### Copy and Move Files

```python
from swap_layer.storage.factory import get_storage_provider

storage = get_storage_provider()

# Copy a file
storage.copy_file(
    source_path='uploads/photo.jpg',
    destination_path='backups/photo.jpg'
)

# Move/rename a file
storage.move_file(
    source_path='uploads/temp.jpg',
    destination_path='uploads/final.jpg'
)
```

### Bulk Operations

```python
from swap_layer.storage.factory import get_storage_provider

storage = get_storage_provider()

# Delete multiple files
result = storage.delete_files([
    'uploads/old1.jpg',
    'uploads/old2.jpg',
    'uploads/old3.jpg',
])

print(f"Deleted: {len(result['deleted'])}")
print(f"Errors: {len(result['errors'])}")
```

## Providers

### Local File Storage (Built-in)

The default provider stores files on the local filesystem.

**Pros:**
- No external dependencies
- No additional costs
- Fast for development
- Simple setup

**Cons:**
- Not suitable for multi-server deployments
- No automatic backups
- Limited scalability

**Configuration:**
```python
STORAGE_PROVIDER = 'local'
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'
```

### AWS S3 (Stub - Needs Implementation)

AWS S3 is a scalable object storage service.

**To implement:**
1. Install: `pip install boto3`
2. Complete the stub implementation in `providers/s3.py`
3. Configure AWS credentials

**Pros:**
- Highly scalable
- Built-in CDN (CloudFront)
- Automatic backups/versioning
- Industry standard

**Cons:**
- Additional costs
- Requires AWS account
- More complex setup

### Azure Blob Storage (Stub - Needs Implementation)

Azure Blob Storage is Microsoft's object storage solution.

**To implement:**
1. Install: `pip install azure-storage-blob`
2. Complete the stub implementation in `providers/azure.py`
3. Configure Azure credentials

**Pros:**
- Integrates with Azure ecosystem
- Good for Microsoft-centric infrastructure
- Competitive pricing

**Cons:**
- Requires Azure account
- Additional costs

## Testing

### Unit Tests with Mocks

```python
from unittest.mock import Mock, patch
from swap_layer.storage.adapter import StorageProviderAdapter

# Mock the storage provider
mock_storage = Mock(spec=StorageProviderAdapter)
mock_storage.upload_file.return_value = {
    'url': 'https://example.com/test.jpg',
    'file_path': 'test.jpg',
    'size': 1024,
    'content_type': 'image/jpeg',
    'etag': 'abc123',
}

# Use in your tests
with patch('swap_layer.storage.factory.get_storage_provider', return_value=mock_storage):
    # Your test code here
    pass
```

## Adding a New Provider

To add support for a new storage provider (e.g., Google Cloud Storage):

1. Create a new file: `providers/gcs.py`

2. Implement the `StorageProviderAdapter` interface:

```python
from swap_layer.storage.adapter import StorageProviderAdapter

class GCSStorageProvider(StorageProviderAdapter):
    def __init__(self):
        # Initialize Google Cloud Storage client
        pass
    
    def upload_file(self, file_path, file_data, content_type=None, metadata=None, public=False):
        # Implement using GCS client
        pass
    
    # Implement all other abstract methods...
```

3. Update `factory.py`:

```python
def get_storage_provider():
    provider = getattr(settings, 'STORAGE_PROVIDER', 'local').lower()
    
    if provider == 'local':
        return LocalFileStorageProvider()
    elif provider == 's3':
        return S3StorageProvider()
    elif provider == 'azure':
        return AzureBlobStorageProvider()
    elif provider == 'gcs':
        from swap_layer.storage.providers.gcs import GCSStorageProvider
        return GCSStorageProvider()
    # ...
```

4. Add configuration to `settings.py`:

```python
# Google Cloud Storage Configuration
GCS_PROJECT_ID = os.environ.get('GCS_PROJECT_ID')
GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME')
GCS_CREDENTIALS_FILE = os.environ.get('GCS_CREDENTIALS_FILE')
```

## Best Practices

1. **Use descriptive file paths**: Include context in paths (e.g., `uploads/{user_id}/{year}/{month}/filename.jpg`)

2. **Set appropriate access control**: Use `public=True` only for files that should be publicly accessible

3. **Clean up old files**: Implement lifecycle policies or cleanup jobs for temporary files

4. **Validate file types**: Check file extensions and MIME types before upload

5. **Set file size limits**: Implement upload size restrictions at the application level

6. **Use presigned URLs**: For large files, use presigned URLs to avoid uploading through your server

7. **Handle errors gracefully**: Wrap storage operations in try-except blocks

8. **Consider costs**: Monitor storage and bandwidth costs, especially with cloud providers

## Error Handling

The abstraction defines custom exceptions:

```python
from swap_layer.storage.adapter import (
    StorageError,                # Base exception
    StorageUploadError,          # Upload failures
    StorageDownloadError,        # Download failures
    StorageFileNotFoundError,    # File not found
    StorageDeleteError,          # Deletion failures
    StorageCopyError,            # Copy failures
    StorageMoveError,            # Move failures
)

# Handle errors
try:
    storage.upload_file('test.jpg', file_data)
except StorageUploadError as e:
    print(f"Upload failed: {e}")
except StorageError as e:
    print(f"Storage error: {e}")
```

## Comparison with Other Abstractions

| Aspect | Authentication | Payments | Email | **Storage** |
|--------|---------------|----------|-------|-------------|
| **Location** | `swap_layer/identity/platform/` | `swap_layer/payments/` | `swap_layer/email/` | `swap_layer/storage/` |
| **Base Class** | `AuthProviderAdapter` | `PaymentProviderAdapter` | `EmailProviderAdapter` | `StorageProviderAdapter` |
| **Factory** | `get_identity_client()` | `get_payment_provider()` | `get_email_provider()` | `get_storage_provider()` |
| **Methods** | 3 | 21 | 8 | 12 |
| **Providers** | Auth0, WorkOS | Stripe | SMTP, SendGrid, Mailgun, SES | Local, S3 (stub), Azure (stub) |
| **Config Key** | `IDENTITY_PROVIDER` | `PAYMENT_PROVIDER` | `EMAIL_PROVIDER` | `STORAGE_PROVIDER` |
| **Pattern** | Provider Adapter | Provider Adapter | Provider Adapter | Provider Adapter |

All abstractions follow the same architectural pattern for consistency and ease of use.

## Benefits

1. **Provider Independence** - Switch storage providers by changing one setting
2. **Consistent Interface** - Same API regardless of provider
3. **Easy Testing** - Mock the adapter interface for unit tests
4. **Gradual Migration** - Migrate from one provider to another without downtime
5. **Cost Optimization** - Switch to cheaper providers as your needs change
6. **Multi-Provider Support** - Use different providers for different use cases
7. **Future-Proof** - Easy to add new providers as they emerge

## Security Considerations

1. **Access Control**: Use `public=False` for sensitive files and generate signed URLs
2. **Validation**: Always validate file types and sizes before upload
3. **Encryption**: Enable encryption at rest and in transit (supported by S3/Azure)
4. **Credentials**: Store provider credentials in environment variables, never in code
5. **URL Expiration**: Set appropriate expiration times for presigned URLs
6. **Audit Logging**: Log all storage operations for security audits

## Performance Tips

1. **Async Uploads**: For large files, use background tasks (Celery) for uploads
2. **CDN Integration**: Use CloudFront (S3) or Azure CDN for faster downloads
3. **Compression**: Compress files before upload when appropriate
4. **Caching**: Cache file URLs to reduce provider API calls
5. **Batch Operations**: Use bulk delete operations instead of individual deletes

## License

This module is part of SwapLayer and follows the MIT License.
