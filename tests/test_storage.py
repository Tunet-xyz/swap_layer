import unittest
from io import BytesIO
from unittest.mock import MagicMock, mock_open, patch

from django.conf import settings

from swap_layer.storage.adapter import StorageProviderAdapter
from swap_layer.storage.factory import get_storage_provider
from swap_layer.storage.providers.django_storage import DjangoStorageAdapter
from swap_layer.storage.providers.local import LocalFileStorageProvider


class TestStorageFactory(unittest.TestCase):
    def test_get_storage_provider_returns_local(self):
        """Test that the factory returns the correct provider based on settings."""
        with patch.object(settings, "STORAGE_PROVIDER", "local"):
            provider = get_storage_provider()
            self.assertIsInstance(provider, LocalFileStorageProvider)
            self.assertIsInstance(provider, StorageProviderAdapter)

    def test_factory_raises_for_unknown_provider(self):
        """Test that the factory raises ValueError for unknown providers."""
        from swap_layer.settings import SwapLayerSettings

        # Create mock settings with unknown provider
        mock_settings = SwapLayerSettings(storage={"provider": "local"})
        # Override provider to invalid value after creation
        mock_settings.storage.provider = "unknown"

        with patch("swap_layer.storage.factory.get_swaplayer_settings", return_value=mock_settings):
            with self.assertRaises(ValueError):
                get_storage_provider()


class TestLocalStorageProvider(unittest.TestCase):
    def setUp(self):
        self.provider = LocalFileStorageProvider()

    @patch("builtins.open", new_callable=mock_open)
    def test_upload_file_success(self, mock_file):
        """Test successful file upload."""
        file_data = BytesIO(b"test file content")

        with patch("swap_layer.storage.providers.local.Path.mkdir"):
            with patch("swap_layer.storage.providers.local.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = 17
                with patch.object(self.provider, "_calculate_etag", return_value="abc123"):
                    result = self.provider.upload_file(
                        file_path="uploads/test.txt",
                        file_data=file_data,
                        content_type="text/plain",
                        metadata={"user_id": "123"},
                    )

        self.assertEqual(result["file_path"], "uploads/test.txt")
        self.assertIn("/media/uploads/test.txt", result["url"])
        self.assertEqual(result["size"], 17)
        self.assertEqual(result["content_type"], "text/plain")

    @patch("builtins.open", new_callable=mock_open, read_data=b"file content")
    def test_download_file_success(self, mock_file):
        """Test successful file download."""
        with patch("swap_layer.storage.providers.local.Path.exists", return_value=True):
            result = self.provider.download_file("uploads/test.txt")

        self.assertEqual(result, b"file content")

    @patch("swap_layer.storage.providers.local.Path.exists", return_value=False)
    def test_download_file_not_found(self, mock_exists):
        """Test downloading non-existent file raises error."""
        from swap_layer.storage.adapter import StorageFileNotFoundError

        with self.assertRaises(StorageFileNotFoundError):
            self.provider.download_file("nonexistent.txt")

    @patch("swap_layer.storage.providers.local.Path.exists", return_value=True)
    @patch("swap_layer.storage.providers.local.Path.unlink")
    def test_delete_file_success(self, mock_unlink, mock_exists):
        """Test successful file deletion."""
        result = self.provider.delete_file("uploads/test.txt")

        self.assertTrue(result["deleted"])

    def test_file_exists(self):
        """Test checking if file exists."""
        with patch("swap_layer.storage.providers.local.Path.exists", return_value=True):
            with patch("swap_layer.storage.providers.local.Path.is_file", return_value=True):
                result = self.provider.file_exists("uploads/test.txt")

                self.assertTrue(result)

    @patch("swap_layer.storage.providers.local.Path.exists", return_value=False)
    def test_file_not_exists(self, mock_exists):
        """Test checking non-existent file."""
        result = self.provider.file_exists("nonexistent.txt")

        self.assertFalse(result)

    def test_get_file_metadata(self):
        """Test retrieving file metadata."""
        with patch("swap_layer.storage.providers.local.Path.exists", return_value=True):
            with patch("swap_layer.storage.providers.local.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = 1024
                mock_stat.return_value.st_mtime = 1640000000
                with patch.object(self.provider, "_calculate_etag", return_value="abc123"):
                    with patch("builtins.open", mock_open(read_data="")):
                        result = self.provider.get_file_metadata("uploads/test.txt")

        self.assertEqual(result["size"], 1024)
        self.assertIn("last_modified", result)

    def test_list_files(self):
        """Test listing files with prefix."""
        from pathlib import Path

        with patch("swap_layer.storage.providers.local.Path.exists", return_value=True):
            with patch("swap_layer.storage.providers.local.Path.rglob") as mock_rglob:
                mock_files = []
                for name in ["file1.txt", "file2.pdf", "photo1.jpg"]:
                    mock_file = MagicMock(spec=Path)
                    mock_file.is_file.return_value = True
                    mock_file.suffix = (
                        ".txt" if "txt" in name else (".pdf" if "pdf" in name else ".jpg")
                    )
                    mock_file.relative_to.return_value = Path(f"uploads/{name}")
                    mock_file.stat.return_value.st_size = 100
                    mock_file.stat.return_value.st_mtime = 1640000000
                    mock_files.append(mock_file)
                mock_rglob.return_value = mock_files

                with patch.object(self.provider, "_calculate_etag", return_value="abc123"):
                    result = self.provider.list_files(prefix="uploads/")

        self.assertEqual(len(result), 3)
        self.assertTrue(any("file1.txt" in f["file_path"] for f in result))

    @patch("swap_layer.storage.providers.local.shutil.copy2")
    def test_copy_file(self, mock_copy):
        """Test copying a file."""
        with patch("swap_layer.storage.providers.local.Path.exists", return_value=True):
            with patch("swap_layer.storage.providers.local.Path.mkdir"):
                with patch.object(self.provider, "_calculate_etag", return_value="abc123"):
                    result = self.provider.copy_file(
                        source_path="uploads/original.txt", destination_path="backups/copy.txt"
                    )

        self.assertEqual(result["source_path"], "uploads/original.txt")
        self.assertEqual(result["destination_path"], "backups/copy.txt")

    @patch("swap_layer.storage.providers.local.shutil.move")
    def test_move_file(self, mock_move):
        """Test moving/renaming a file."""
        with patch("swap_layer.storage.providers.local.Path.exists", return_value=True):
            with patch("swap_layer.storage.providers.local.Path.mkdir"):
                result = self.provider.move_file(
                    source_path="uploads/temp.txt", destination_path="uploads/final.txt"
                )

        self.assertEqual(result["source_path"], "uploads/temp.txt")
        self.assertEqual(result["destination_path"], "uploads/final.txt")

    def test_delete_files_bulk(self):
        """Test bulk file deletion."""
        files = ["file1.txt", "file2.txt", "file3.txt"]

        with patch("swap_layer.storage.providers.local.Path.exists", return_value=True):
            with patch("swap_layer.storage.providers.local.Path.unlink"):
                result = self.provider.delete_files(files)

        self.assertEqual(len(result["deleted"]), 3)
        self.assertEqual(len(result["errors"]), 0)

    def test_get_file_url(self):
        """Test generating file URL."""
        result = self.provider.get_file_url("uploads/test.txt")

        self.assertIn("/media/uploads/test.txt", result)
        self.assertIsInstance(result, str)


class TestDjangoStorageProvider(unittest.TestCase):
    """Tests for DjangoStorageAdapter wrapping django-storages."""

    def setUp(self):
        self.provider = DjangoStorageAdapter()

    @patch("swap_layer.storage.providers.django_storage.default_storage")
    def test_upload_file_success(self, mock_storage):
        """Test successful file upload via django-storages."""
        file_data = BytesIO(b"test content")
        mock_storage.save.return_value = "uploads/test.txt"
        mock_storage.url.return_value = "https://s3.amazonaws.com/bucket/uploads/test.txt"
        mock_storage.size.return_value = 12

        result = self.provider.upload_file(
            file_path="uploads/test.txt", file_data=file_data, content_type="text/plain"
        )

        self.assertEqual(result["file_path"], "uploads/test.txt")
        self.assertEqual(result["url"], "https://s3.amazonaws.com/bucket/uploads/test.txt")
        self.assertEqual(result["size"], 12)
        mock_storage.save.assert_called_once()

    @patch("swap_layer.storage.providers.django_storage.default_storage")
    def test_download_file_success(self, mock_storage):
        """Test downloading a file via django-storages."""
        mock_file = MagicMock()
        mock_file.read.return_value = b"file content"
        mock_storage.open.return_value.__enter__.return_value = mock_file
        mock_storage.exists.return_value = True

        result = self.provider.download_file("uploads/test.txt")

        self.assertEqual(result, b"file content")
        mock_storage.open.assert_called_once_with("uploads/test.txt", "rb")

    @patch("swap_layer.storage.providers.django_storage.default_storage")
    def test_download_file_not_found(self, mock_storage):
        """Test downloading non-existent file raises error."""
        from swap_layer.storage.adapter import StorageFileNotFoundError

        mock_storage.exists.return_value = False

        with self.assertRaises(StorageFileNotFoundError):
            self.provider.download_file("nonexistent.txt")

    @patch("swap_layer.storage.providers.django_storage.default_storage")
    def test_delete_file_success(self, mock_storage):
        """Test deleting a file via django-storages."""
        mock_storage.exists.return_value = True

        result = self.provider.delete_file("uploads/test.txt")

        self.assertTrue(result["deleted"])
        self.assertEqual(result["file_path"], "uploads/test.txt")
        mock_storage.delete.assert_called_once_with("uploads/test.txt")

    @patch("swap_layer.storage.providers.django_storage.default_storage")
    def test_file_exists(self, mock_storage):
        """Test checking if file exists."""
        mock_storage.exists.return_value = True

        result = self.provider.file_exists("uploads/test.txt")

        self.assertTrue(result)
        mock_storage.exists.assert_called_once_with("uploads/test.txt")

    @patch("swap_layer.storage.providers.django_storage.default_storage")
    def test_get_file_metadata(self, mock_storage):
        """Test retrieving file metadata."""
        from datetime import datetime

        mock_storage.exists.return_value = True
        mock_storage.size.return_value = 1024
        mock_storage.get_modified_time.return_value = datetime(2026, 1, 1, 12, 0, 0)
        mock_storage.get_created_time.return_value = datetime(2026, 1, 1, 10, 0, 0)

        result = self.provider.get_file_metadata("uploads/file.txt")

        self.assertEqual(result["size"], 1024)
        self.assertIn("modified_time", result)

    @patch("swap_layer.storage.providers.django_storage.default_storage")
    def test_list_files(self, mock_storage):
        """Test listing files with prefix."""
        mock_storage.listdir.return_value = ([], ["file1.txt", "file2.pdf"])

        result = self.provider.list_files(prefix="uploads/")

        self.assertEqual(len(result["files"]), 2)
        self.assertIn("file1.txt", result["files"])

    @patch("swap_layer.storage.providers.django_storage.default_storage")
    def test_get_file_url(self, mock_storage):
        """Test generating file URL."""
        mock_storage.url.return_value = "https://s3.amazonaws.com/bucket/uploads/test.txt"

        result = self.provider.get_file_url("uploads/test.txt")

        self.assertEqual(result, "https://s3.amazonaws.com/bucket/uploads/test.txt")
        mock_storage.url.assert_called_once_with("uploads/test.txt")

    @patch("swap_layer.storage.providers.django_storage.default_storage")
    def test_copy_file(self, mock_storage):
        """Test copying a file."""
        mock_storage.exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = b"content"
        mock_storage.open.return_value.__enter__.return_value = mock_file
        mock_storage.save.return_value = "destination.txt"

        result = self.provider.copy_file("source.txt", "destination.txt")

        self.assertEqual(result["source_path"], "source.txt")
        self.assertEqual(result["destination_path"], "destination.txt")

    @patch("swap_layer.storage.providers.django_storage.default_storage")
    def test_move_file(self, mock_storage):
        """Test moving a file."""
        mock_storage.exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = b"content"
        mock_storage.open.return_value.__enter__.return_value = mock_file
        mock_storage.save.return_value = "destination.txt"

        result = self.provider.move_file("source.txt", "destination.txt")

        self.assertEqual(result["source_path"], "source.txt")
        self.assertEqual(result["destination_path"], "destination.txt")
        mock_storage.delete.assert_called_once_with("source.txt")

    @patch("swap_layer.storage.providers.django_storage.default_storage")
    def test_delete_files_bulk(self, mock_storage):
        """Test bulk file deletion."""
        mock_storage.exists.side_effect = [True, True, False]

        result = self.provider.delete_files(["file1.txt", "file2.txt", "file3.txt"])

        self.assertEqual(len(result["deleted"]), 2)
        self.assertEqual(len(result["errors"]), 1)

    @patch("swap_layer.storage.providers.django_storage.default_storage")
    def test_upload_file_with_metadata(self, mock_storage):
        """Test uploading file with metadata."""
        file_data = BytesIO(b"test content")
        mock_storage.save.return_value = "uploads/test.txt"
        mock_storage.url.return_value = "https://s3.amazonaws.com/bucket/uploads/test.txt"
        mock_storage.size.return_value = 12

        result = self.provider.upload_file(
            file_path="uploads/test.txt",
            file_data=file_data,
            content_type="text/plain",
            metadata={"user_id": "123"},
            public=True,
        )

        self.assertEqual(result["file_path"], "uploads/test.txt")
        self.assertEqual(result["content_type"], "text/plain")

    def test_generate_presigned_url_not_implemented(self):
        """Test that presigned URLs raise NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            self.provider.generate_presigned_upload_url("test.txt")


if __name__ == "__main__":
    unittest.main()
