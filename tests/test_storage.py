import unittest
from unittest.mock import MagicMock, patch, mock_open
from io import BytesIO
from swap_layer.config import settings
from swap_layer.storage.factory import get_storage_provider
from swap_layer.storage.adapter import StorageProviderAdapter
from swap_layer.storage.providers.local import LocalFileStorageProvider


class TestStorageFactory(unittest.TestCase):
    def test_get_storage_provider_returns_local(self):
        """Test that the factory returns the correct provider based on settings."""
        def mock_get(key, default=None):
            if key == 'STORAGE_PROVIDER': return 'local'
            if key == 'MEDIA_ROOT': return '/tmp/media'
            if key == 'MEDIA_URL': return '/media/'
            return default
            
        with patch.object(settings, 'get', side_effect=mock_get):
            provider = get_storage_provider()
            self.assertIsInstance(provider, LocalFileStorageProvider)
            self.assertIsInstance(provider, StorageProviderAdapter)

    def test_factory_raises_for_unknown_provider(self):
        """Test that the factory raises ValueError for unknown providers."""
        with patch.object(settings, 'get', return_value='unknown'):
            with self.assertRaises(ValueError):
                get_storage_provider()


class TestLocalStorageProvider(unittest.TestCase):
    def setUp(self):
        self.settings_patcher = patch.object(settings, 'get')
        self.mock_get = self.settings_patcher.start()
        def mock_settings_get(key, default=None):
            config = {
                'MEDIA_ROOT': '/tmp/media',
                'MEDIA_URL': '/media/'
            }
            return config.get(key, default)
        self.mock_get.side_effect = mock_settings_get
        
        self.provider = LocalFileStorageProvider()

    def tearDown(self):
        self.settings_patcher.stop()

    @patch('swap_layer.storage.providers.local.os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    def test_upload_file_success(self, mock_file, mock_makedirs):
        """Test successful file upload."""
        file_data = BytesIO(b'test file content')
        
        with patch('swap_layer.storage.providers.local.os.path.getsize', return_value=17):
            result = self.provider.upload_file(
                file_path='uploads/test.txt',
                file_data=file_data,
                content_type='text/plain',
                metadata={'user_id': '123'}
            )

        self.assertEqual(result['file_path'], 'uploads/test.txt')
        self.assertIn('/media/uploads/test.txt', result['url'])
        self.assertEqual(result['size'], 17)
        self.assertEqual(result['content_type'], 'text/plain')

    @patch('swap_layer.storage.providers.local.os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data=b'file content')
    def test_download_file_success(self, mock_file, mock_exists):
        """Test successful file download."""
        result = self.provider.download_file('uploads/test.txt')
        
        self.assertEqual(result, b'file content')
        mock_file.assert_called_with('/tmp/media/uploads/test.txt', 'rb')

    @patch('swap_layer.storage.providers.local.os.path.exists', return_value=False)
    def test_download_file_not_found(self, mock_exists):
        """Test downloading non-existent file raises error."""
        from swap_layer.storage.adapter import StorageFileNotFoundError
        
        with self.assertRaises(StorageFileNotFoundError):
            self.provider.download_file('nonexistent.txt')

    @patch('swap_layer.storage.providers.local.os.path.exists', return_value=True)
    @patch('swap_layer.storage.providers.local.os.remove')
    def test_delete_file_success(self, mock_remove, mock_exists):
        """Test successful file deletion."""
        result = self.provider.delete_file('uploads/test.txt')
        
        self.assertTrue(result['success'])
        mock_remove.assert_called_with('/tmp/media/uploads/test.txt')

    @patch('swap_layer.storage.providers.local.os.path.exists', return_value=True)
    def test_file_exists(self, mock_exists):
        """Test checking if file exists."""
        result = self.provider.file_exists('uploads/test.txt')
        
        self.assertTrue(result)
        mock_exists.assert_called_with('/tmp/media/uploads/test.txt')

    @patch('swap_layer.storage.providers.local.os.path.exists', return_value=False)
    def test_file_not_exists(self, mock_exists):
        """Test checking non-existent file."""
        result = self.provider.file_exists('nonexistent.txt')
        
        self.assertFalse(result)

    @patch('swap_layer.storage.providers.local.os.path.exists', return_value=True)
    @patch('swap_layer.storage.providers.local.os.path.getsize', return_value=1024)
    @patch('swap_layer.storage.providers.local.os.path.getmtime', return_value=1640000000)
    def test_get_file_metadata(self, mock_mtime, mock_size, mock_exists):
        """Test retrieving file metadata."""
        result = self.provider.get_file_metadata('uploads/test.txt')
        
        self.assertEqual(result['file_path'], 'uploads/test.txt')
        self.assertEqual(result['size'], 1024)
        self.assertIn('last_modified', result)

    @patch('swap_layer.storage.providers.local.os.walk')
    def test_list_files(self, mock_walk):
        """Test listing files with prefix."""
        mock_walk.return_value = [
            ('/tmp/media/uploads', [], ['file1.txt', 'file2.pdf']),
            ('/tmp/media/uploads/photos', [], ['photo1.jpg'])
        ]
        
        with patch('swap_layer.storage.providers.local.os.path.getsize', return_value=100):
            result = self.provider.list_files(prefix='uploads/')
        
        self.assertEqual(len(result), 3)
        self.assertTrue(any('file1.txt' in f['file_path'] for f in result))

    @patch('swap_layer.storage.providers.local.os.path.exists', return_value=True)
    @patch('swap_layer.storage.providers.local.shutil.copy2')
    def test_copy_file(self, mock_copy, mock_exists):
        """Test copying a file."""
        with patch('swap_layer.storage.providers.local.os.makedirs'):
            result = self.provider.copy_file(
                source_path='uploads/original.txt',
                destination_path='backups/copy.txt'
            )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['destination_path'], 'backups/copy.txt')

    @patch('swap_layer.storage.providers.local.os.path.exists', return_value=True)
    @patch('swap_layer.storage.providers.local.shutil.move')
    def test_move_file(self, mock_move, mock_exists):
        """Test moving/renaming a file."""
        with patch('swap_layer.storage.providers.local.os.makedirs'):
            result = self.provider.move_file(
                source_path='uploads/temp.txt',
                destination_path='uploads/final.txt'
            )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['destination_path'], 'uploads/final.txt')

    @patch('swap_layer.storage.providers.local.os.path.exists', return_value=True)
    @patch('swap_layer.storage.providers.local.os.remove')
    def test_delete_files_bulk(self, mock_remove, mock_exists):
        """Test bulk file deletion."""
        files = ['file1.txt', 'file2.txt', 'file3.txt']
        
        result = self.provider.delete_files(files)
        
        self.assertEqual(len(result['deleted']), 3)
        self.assertEqual(len(result['errors']), 0)
        self.assertEqual(mock_remove.call_count, 3)

    def test_get_file_url(self):
        """Test generating file URL."""
        result = self.provider.get_file_url('uploads/test.txt')
        
        self.assertIn('/media/uploads/test.txt', result['url'])
        self.assertFalse(result['is_signed'])


if __name__ == '__main__':
    unittest.main()
