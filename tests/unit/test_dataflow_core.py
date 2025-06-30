"""
Comprehensive tests for core dataflow functionality.
Tests focus on the main functions with highest impact on coverage.
"""
import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import tempfile
from typing import Dict, List, Tuple
from pathlib import Path

# Import the module under test
from src.dataflow import (
    is_sql_file,
    validate_sql_content,
    normalize_file_path,
    normalize_path_for_platform,
    collect_sql_files,
    safe_input,
    add_back_to_choices,
    Node
)

class TestIsSqlFile(unittest.TestCase):
    """Test the is_sql_file function."""

    def test_is_sql_file_valid_extensions(self):
        """Test valid SQL file extensions."""
        valid_files = [
            "test.sql", "test.vql", "test.ddl", "test.dml",
            "test.hql", "test.pls", "test.plsql", "test.proc",
            "test.psql", "test.tsql", "test.view"
        ]
        
        for file_path in valid_files:
            with self.subTest(file=file_path):
                self.assertTrue(is_sql_file(file_path))

    def test_is_sql_file_invalid_extensions(self):
        """Test invalid file extensions."""
        invalid_files = [
            "test.txt", "test.py", "test.js", "test.md",
            "test", "test.sql.bak", "readme.txt"
        ]
        
        for file_path in invalid_files:
            with self.subTest(file=file_path):
                self.assertFalse(is_sql_file(file_path))

    def test_is_sql_file_case_insensitive(self):
        """Test case insensitive extension matching."""
        case_variants = [
            "test.SQL", "test.VQL", "test.DDL", "test.DML"
        ]
        
        for file_path in case_variants:
            with self.subTest(file=file_path):
                self.assertTrue(is_sql_file(file_path))

class TestValidateSqlContent(unittest.TestCase):
    """Test the validate_sql_content function."""

    @patch("builtins.open", new_callable=mock_open)
    def test_validate_sql_content_valid_sql(self, mock_file):
        """Test validation of valid SQL content."""
        sql_contents = [
            "CREATE TABLE test (id INT);",
            "SELECT * FROM users;",
            "CREATE VIEW test_view AS SELECT * FROM table1;",
            "INSERT INTO table VALUES (1, 'test');",
            "UPDATE table SET name = 'test' WHERE id = 1;",
            "DELETE FROM table WHERE id = 1;",
            "DROP TABLE test;",
            "ALTER TABLE test ADD COLUMN name VARCHAR(50);"
        ]
        
        for content in sql_contents:
            with self.subTest(content=content[:20]):
                mock_file.return_value.read.return_value = content
                self.assertTrue(validate_sql_content("test.sql"))

    @patch("builtins.open", new_callable=mock_open)
    def test_validate_sql_content_invalid_sql(self, mock_file):
        """Test validation of invalid SQL content."""
        invalid_contents = [
            "This is just text",
            "#!/bin/bash\necho 'hello'",
            "import sys\nprint('hello')",
            "// JavaScript comment\nfunction test() {}"
        ]
        
        for content in invalid_contents:
            with self.subTest(content=content[:20]):
                mock_file.return_value.read.return_value = content
                self.assertFalse(validate_sql_content("test.txt"))

    @patch("builtins.open", side_effect=Exception("File error"))
    def test_validate_sql_content_file_error(self, mock_file):
        """Test validation when file cannot be read."""
        self.assertFalse(validate_sql_content("nonexistent.sql"))

class TestNormalizeFilePath(unittest.TestCase):
    """Test the normalize_file_path function."""

    def test_normalize_file_path_basic(self):
        """Test basic file path normalization."""
        path = "/home/user/test.sql"
        result = normalize_file_path(path)
        self.assertTrue(os.path.isabs(result))

    def test_normalize_file_path_with_quotes(self):
        """Test normalization of quoted paths."""
        quoted_paths = [
            "'/home/user/test.sql'",
            '"/home/user/test.sql"',
            "  '/home/user/test.sql'  "
        ]
        
        for path in quoted_paths:
            with self.subTest(path=path):
                result = normalize_file_path(path)
                self.assertNotIn('"', result)
                self.assertNotIn("'", result)

    def test_normalize_file_path_file_uri(self):
        """Test normalization of file:// URIs."""
        file_uris = [
            "file:///home/user/test.sql",
            "file://localhost/home/user/test.sql",
            "file:/home/user/test.sql"
        ]
        
        for uri in file_uris:
            with self.subTest(uri=uri):
                result = normalize_file_path(uri)
                self.assertNotIn("file://", result)

    def test_normalize_file_path_url_encoded(self):
        """Test normalization of URL-encoded paths."""
        encoded_path = "file:///home/user/test%20file.sql"
        result = normalize_file_path(encoded_path)
        self.assertIn("test file.sql", result)
        self.assertNotIn("%20", result)

    @patch('pathlib.Path.resolve', side_effect=OSError("Resolution failed"))
    def test_normalize_file_path_resolution_error(self, mock_resolve):
        """Test normalization when path resolution fails."""
        path = "/problematic/path"
        result = normalize_file_path(path)
        self.assertEqual(result, path)

class TestNormalizePathForPlatform(unittest.TestCase):
    """Test the normalize_path_for_platform function."""

    @patch('os.name', 'nt')
    def test_normalize_path_for_platform_windows(self):
        """Test Windows path normalization."""
        unix_path = "/home/user/test.sql"
        result = normalize_path_for_platform(unix_path)
        # Should convert forward slashes to backslashes on Windows
        self.assertIn("\\", result.replace(":", ""))  # Exclude drive letter colon

    @patch('os.name', 'posix')
    def test_normalize_path_for_platform_unix(self):
        """Test Unix path normalization."""
        path_with_spaces = "/home/user/test file.sql"
        result = normalize_path_for_platform(path_with_spaces)
        # Should quote paths with spaces on Unix
        self.assertTrue(result.startswith('"') or result.startswith("'") or " " not in result)

class TestCollectSqlFiles(unittest.TestCase):
    """Test the collect_sql_files function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Create test files
        (self.temp_path / "test1.sql").write_text("CREATE TABLE test1;")
        (self.temp_path / "test2.vql").write_text("CREATE VIEW test2;")
        (self.temp_path / "test3.txt").write_text("Not SQL")
        
        # Create subdirectory with more files
        sub_dir = self.temp_path / "subdir"
        sub_dir.mkdir()
        (sub_dir / "test4.sql").write_text("CREATE TABLE test4;")

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_collect_sql_files_default_directories(self):
        """Test collecting files from default directories."""
        with patch('pathlib.Path.cwd', return_value=self.temp_path), \
             patch('pathlib.Path.home', return_value=self.temp_path), \
             patch('src.path_utils.DATA_FLOW_BASE_DIR', self.temp_path):
            
            files = collect_sql_files()
            
            # Should find SQL files but not text files
            sql_files = [f for f in files if f.endswith(('.sql', '.vql'))]
            self.assertGreater(len(sql_files), 0)
            
            # Should not find text files
            txt_files = [f for f in files if f.endswith('.txt')]
            self.assertEqual(len(txt_files), 0)

    def test_collect_sql_files_specific_directories(self):
        """Test collecting files from specific directories."""
        files = collect_sql_files([self.temp_path])
        
        # Should find both SQL files
        self.assertGreater(len(files), 0)
        sql_files = [f for f in files if f.endswith(('.sql', '.vql'))]
        self.assertGreaterEqual(len(sql_files), 2)

    @patch('shutil.which')
    def test_collect_sql_files_with_fd_command(self, mock_which):
        """Test collecting files using fd command."""
        mock_which.return_value = "/usr/bin/fd"
        
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "test1.sql\ntest2.vql\n"
            mock_run.return_value = mock_result
            
            files = collect_sql_files([self.temp_path])
            
            # Should call fd command
            mock_run.assert_called()
            self.assertGreater(len(files), 0)

    @patch('shutil.which', return_value=None)
    def test_collect_sql_files_fallback_to_python(self, mock_which):
        """Test fallback to Python when fd is not available."""
        files = collect_sql_files([self.temp_path])
        
        # Should still find files using Python fallback
        sql_files = [f for f in files if f.endswith(('.sql', '.vql'))]
        self.assertGreater(len(sql_files), 0)

    def test_collect_sql_files_nonexistent_directory(self):
        """Test collecting files from non-existent directory."""
        nonexistent_path = Path("/nonexistent/directory")
        files = collect_sql_files([nonexistent_path])
        
        # Should return empty list without error
        self.assertEqual(files, [])

class TestSafeInput(unittest.TestCase):
    """Test the safe_input function."""

    @patch('builtins.input', return_value="test input")
    def test_safe_input_normal(self, mock_input):
        """Test normal input handling."""
        result = safe_input("Enter text: ")
        self.assertEqual(result, "test input")

    @patch('builtins.input', side_effect=KeyboardInterrupt())
    def test_safe_input_keyboard_interrupt(self, mock_input):
        """Test handling of keyboard interrupt."""
        with patch('builtins.print'):  # Suppress print output
            result = safe_input("Enter text: ")
        self.assertIsNone(result)

class TestAddBackToChoices(unittest.TestCase):
    """Test the add_back_to_choices function."""

    def test_add_back_to_choices_basic(self):
        """Test adding back option to choices."""
        choices = ["Option 1", "Option 2", "Option 3"]
        result = add_back_to_choices(choices)
        
        self.assertEqual(len(result), len(choices) + 1)
        self.assertIn("← Go back", result)
        self.assertEqual(result[-1], "← Go back")

    def test_add_back_to_choices_empty_list(self):
        """Test adding back option to empty choices."""
        choices = []
        result = add_back_to_choices(choices)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "← Go back")

    def test_add_back_to_choices_preserves_order(self):
        """Test that original choice order is preserved."""
        choices = ["First", "Second", "Third"]
        result = add_back_to_choices(choices)
        
        # Original choices should be in same order
        for i, choice in enumerate(choices):
            self.assertEqual(result[i], choice)

class TestNode(unittest.TestCase):
    """Test the Node class."""

    def test_node_creation_basic(self):
        """Test basic node creation."""
        node = Node("table", "test_table")
        
        self.assertEqual(node.node_type, "table")
        self.assertEqual(node.name, "test_table")
        self.assertFalse(node.enabled)

    def test_node_creation_with_enabled(self):
        """Test node creation with enabled flag."""
        node = Node("view", "test_view", enabled=True)
        
        self.assertEqual(node.node_type, "view")
        self.assertEqual(node.name, "test_view")
        self.assertTrue(node.enabled)

    def test_node_attributes_modification(self):
        """Test modification of node attributes."""
        node = Node("table", "test_table")
        
        # Modify attributes
        node.enabled = True
        node.name = "modified_table"
        node.node_type = "view"
        
        # Verify changes
        self.assertTrue(node.enabled)
        self.assertEqual(node.name, "modified_table")
        self.assertEqual(node.node_type, "view")

if __name__ == "__main__":
    unittest.main()
