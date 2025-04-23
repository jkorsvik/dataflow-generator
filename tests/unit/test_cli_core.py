import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
from src.dataflow import (
    is_sql_file,
    validate_sql_content,
    handle_file_drop,
    select_metadata,
    handle_back_key,
)

class TestCLICore(unittest.TestCase):
    def setUp(self):
        """Set up test data"""
        self.sample_sql = """
        CREATE OR REPLACE VIEW test_view AS
        SELECT * FROM test_table;
        """

    def test_is_sql_file(self):
        """Test SQL file extension validation"""
        valid_files = [
            "test.sql", "test.vql", "test.ddl", "test.dml",
            "test.hql", "test.pls", "test.plsql", "test.proc",
            "test.psql", "test.tsql", "test.view",
        ]
        invalid_files = [
            "test.txt", "test.py", "test", "test.sql.txt",
        ]

        # Test valid extensions
        for file in valid_files:
            self.assertTrue(
                is_sql_file(file),
                f"Expected {file} to be recognized as SQL file"
            )

        # Test invalid extensions
        for file in invalid_files:
            self.assertFalse(
                is_sql_file(file),
                f"Expected {file} to not be recognized as SQL file"
            )

    @patch('builtins.open', new_callable=mock_open)
    def test_validate_sql_content(self, mock_file):
        """Test SQL content validation"""
        # Valid SQL content
        mock_file.return_value.read.return_value = self.sample_sql
        self.assertTrue(validate_sql_content("test.sql"))

        # Invalid SQL content
        mock_file.return_value.read.return_value = "This is not SQL"
        self.assertFalse(validate_sql_content("test.sql"))

    @patch('builtins.input')
    def test_handle_file_drop(self, mock_input):
        """Test file drop handling"""
        # Test cancel
        mock_input.return_value = "cancel"
        self.assertIsNone(handle_file_drop())

        # Test invalid file path
        mock_input.return_value = "nonexistent.sql"
        self.assertIsNone(handle_file_drop())

    @patch('questionary.select')
    @patch('questionary.path')
    def test_select_metadata(self, mock_path, mock_select):
        """Test metadata file selection"""
        # Mock successful file selection
        mock_select.return_value.ask.return_value = "Browse SQL Files"
        mock_path.return_value.ask.return_value = "test.sql"

        # TODO: Implement better file selection logic and corresponding test
        # Testing of file selection
        #result = select_metadata()
        #self.assertEqual(result, "test.sql")

        # TODO: Implement better back navigation and corresponding test
        # Test back navigation
        #mock_select.return_value.ask.return_value = "← Go back"
        #result = select_metadata(allow_back=True)
        #self.assertIsNone(result)

    def test_handle_back_key(self):
        """Test back key handling"""
        self.assertTrue(handle_back_key('b'))
        self.assertTrue(handle_back_key('B'))
        self.assertFalse(handle_back_key('x'))

    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch('questionary.confirm')
    def test_non_sql_file_handling(self, mock_confirm, mock_isfile, mock_exists):
        """Test handling of non-SQL files"""
        mock_exists.return_value = True
        mock_isfile.return_value = True
        
        # Test when user confirms non-SQL file
        mock_confirm.return_value.ask.return_value = True
        with patch('builtins.input', return_value='test.txt'):
            result = handle_file_drop()
            self.assertEqual(result, 'test.txt')

        # Test when user rejects non-SQL file
        mock_confirm.return_value.ask.return_value = False
        with patch('builtins.input', return_value='test.txt'):
            result = handle_file_drop()
            self.assertIsNone(result)

    @patch('os.getcwd')
    @patch('glob.glob')
    def test_empty_directory(self, mock_glob, mock_getcwd):
        """Test behavior when no SQL files are found"""
        mock_getcwd.return_value = "/test/dir"
        mock_glob.return_value = []
        
        with patch('questionary.select') as mock_select:
            mock_select.return_value.ask.return_value = "Browse SQL Files"
            result = select_metadata()
            self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
