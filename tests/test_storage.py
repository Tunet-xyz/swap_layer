import unittest
from io import BytesIO
from unittest.mock import MagicMock, mock_open, patch

from django.conf import settings

from swap_layer.storage.adapter import StorageProviderAdapter
from swap_layer.storage.factory import get_storage_provider
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
        with patch.object(settings, "STORAGE_PROVIDER", "unknown"):
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

    @patch("swap_layer.storage.providers.local.os.path.exists", return_value=False)
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

    @patch("swap_layer.storage.providers.local.os.path.exists", return_value=False)
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


if __name__ == "__main__":
    unittest.main()
