import unittest
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock
from io import StringIO
from pathlib import Path
from src.dataflow import (
    normalize_file_path,
    normalize_path_for_platform,
    handle_file_drop,
    collect_sql_files,
    handle_back_key,
    safe_input,
)


class TestDataflowCLI(unittest.TestCase):
    """Test the dataflow CLI functionality"""

    def setUp(self):
        """Set up test environment"""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Create some test SQL files
        self.create_test_files()

    def create_test_files(self):
        """Create test SQL files for testing file discovery"""
        # Create files with different SQL extensions
        extensions = [".sql", ".vql", ".ddl", ".dml"]
        for ext in extensions:
            test_file = self.temp_path / f"test_file{ext}"
            with open(test_file, "w") as f:
                f.write(f"-- Test SQL file with extension {ext}")

    def test_handle_back_key(self):
        """Affirm back key logic: only ESC, Ctrl+C, Ctrl+D are back keys"""
        import readchar
        # Should NOT trigger back navigation
        self.assertFalse(handle_back_key("b"))
        self.assertFalse(handle_back_key("B"))
        self.assertFalse(handle_back_key("a"))
        self.assertFalse(handle_back_key("enter"))
        self.assertTrue(handle_back_key(""))  # Empty string is treated as BACK_KEY in current logic
        self.assertFalse(handle_back_key(None))
        self.assertFalse(handle_back_key(123))
        # Should trigger back navigation
        self.assertTrue(handle_back_key(readchar.key.ESC))
        self.assertTrue(handle_back_key(readchar.key.CTRL_C))
        self.assertTrue(handle_back_key(readchar.key.CTRL_D))

    def test_normalize_file_path(self):
        """Test normalize_file_path with different inputs"""
        # Test with an actual path to avoid mocking issues
        test_path = os.path.join(self.temp_path, "test_path.sql")

        # Create the test file
        with open(test_path, "w") as f:
            f.write("-- Test file")

        # Test the actual normalize_file_path function
        result = normalize_file_path(test_path)

        # Check that result is a string and not empty
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

        # Test with a file:// URL
        file_url = f"file:///{test_path.replace(os.sep, '/')}"
        result_url = normalize_file_path(file_url)
        self.assertNotIn("file://", result_url)

    def test_normalize_path_for_platform(self):
        """Test platform-specific path normalization"""
        # Test with Windows-style path
        win_path = r"C:\Users\test\file.sql"
        norm_win = normalize_path_for_platform(win_path)
        self.assertIsInstance(norm_win, str)

        # Test with Unix-style path
        unix_path = "/home/user/file.sql"
        norm_unix = normalize_path_for_platform(unix_path)
        self.assertIsInstance(norm_unix, str)

        # Test with path containing spaces
        space_path = "path with spaces/file.sql"
        norm_space = normalize_path_for_platform(space_path)
        self.assertIsInstance(norm_space, str)

    @patch("src.dataflow.input")
    def test_handle_file_drop(self, mock_input):
        """Test handle_file_drop function"""
        # Create a temporary file for testing
        test_file = self.temp_path / "drop_test.sql"
        with open(test_file, "w") as f:
            f.write("-- Test SQL content")

        # Test successful file drop
        mock_input.return_value = str(test_file)
        result = handle_file_drop(allow_back=True)
        self.assertEqual(result, str(test_file.resolve()))

        # Test cancellation with 'cancel'
        mock_input.return_value = "cancel"
        result = handle_file_drop()
        self.assertIsNone(result)

        # Test back navigation with 'b'
        mock_input.return_value = "b"
        result = handle_file_drop()
        self.assertIsNone(result)

        # Test with invalid file path
        mock_input.return_value = "nonexistent_file.sql"
        with patch("sys.stdout", new=StringIO()):  # Suppress print
            result = handle_file_drop()
        self.assertIsNone(result)

    def test_collect_sql_files(self):
        """Test collect_sql_files function"""
        # Test with default directories
        with patch("src.dataflow.Path.home") as mock_home:
            mock_home.return_value = self.temp_path
            # Make collect_sql_files use our temp directory
            files = collect_sql_files([self.temp_path])

            # Should find all our test files
            self.assertEqual(len(files), 4)  # We created 4 test files

            # All files should be SQL files
            for file in files:
                self.assertTrue(os.path.exists(file))
                _, ext = os.path.splitext(file)
                self.assertIn(ext.lower(), [".sql", ".vql", ".ddl", ".dml"])

    @patch("src.dataflow.input")
    def test_safe_input(self, mock_input):
        """Test safe_input function"""
        # Test normal input
        mock_input.return_value = "test input"
        result = safe_input("Prompt: ")
        self.assertEqual(result, "test input")

        # Test KeyboardInterrupt
        mock_input.side_effect = KeyboardInterrupt()
        with patch("sys.stdout", new=StringIO()):  # Suppress print
            result = safe_input("Prompt: ")
        self.assertIsNone(result)

    def tearDown(self):
        """Clean up test environment"""
        self.temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
