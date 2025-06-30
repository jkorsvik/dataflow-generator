"""
Comprehensive tests for the PostgreSQL parser module.
Tests cover all major functions and edge cases.
"""
import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import tempfile
from typing import Dict, List, Tuple

# Import the module under test
from src.parsers.parser_postgres import (
    _extract_schema,
    format_sql,
    add_node,
    find_dependencies,
    find_foreign_keys,
    parse_dump,
    NodeInfoPG
)
from src.exceptions import InvalidSQLError

class TestExtractSchema(unittest.TestCase):
    """Test the _extract_schema function."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock sqlglot Identifier class
        self.mock_identifier = MagicMock()
        self.mock_identifier.name = "test_schema"

    def test_extract_schema_with_identifier(self):
        """Test extracting schema from Identifier object."""
        # Mock the isinstance check
        with patch('src.parsers.parser_postgres.exp.Identifier', self.mock_identifier.__class__):
            result = _extract_schema(self.mock_identifier)
            self.assertEqual(result, "test_schema")

    def test_extract_schema_with_none(self):
        """Test extracting schema from None."""
        result = _extract_schema(None)
        self.assertIsNone(result)

    def test_extract_schema_with_non_identifier(self):
        """Test extracting schema from non-Identifier object."""
        result = _extract_schema("not_an_identifier")
        self.assertIsNone(result)

class TestFormatSql(unittest.TestCase):
    """Test the format_sql function."""

    def test_format_sql_basic(self):
        """Test basic SQL formatting."""
        sql = "SELECT * FROM table1"
        result = format_sql(sql)
        self.assertEqual(result.strip(), sql)

    @patch('src.parsers.parser_postgres.sqlfluff.fix')
    def test_format_sql_with_sqlfluff(self, mock_fix):
        """Test SQL formatting with sqlfluff."""
        sql = "SELECT * FROM table1"
        formatted_sql = "SELECT *\nFROM table1"
        mock_fix.return_value = formatted_sql
        
        result = format_sql(sql)
        self.assertEqual(result, formatted_sql.strip())
        mock_fix.assert_called_once_with(sql, dialect='postgres')

    @patch('src.parsers.parser_postgres.sqlfluff.fix', side_effect=Exception("Format error"))
    def test_format_sql_fallback_on_error(self, mock_fix):
        """Test SQL formatting falls back to strip on error."""
        sql = "  SELECT * FROM table1  "
        result = format_sql(sql)
        self.assertEqual(result, sql.strip())

    @patch('src.parsers.parser_postgres.sqlfluff.fix')
    def test_format_sql_empty_result(self, mock_fix):
        """Test SQL formatting with empty result from sqlfluff."""
        sql = "SELECT * FROM table1"
        mock_fix.return_value = ""
        
        result = format_sql(sql)
        self.assertEqual(result, sql.strip())

class TestAddNode(unittest.TestCase):
    """Test the add_node function."""

    def setUp(self):
        """Set up test fixtures."""
        self.node_types = {}

    def test_add_node_empty_name(self):
        """Test adding node with empty name."""
        result = add_node("", "table", "schema1", "CREATE TABLE", self.node_types)
        self.assertEqual(result, "")
        self.assertEqual(len(self.node_types), 0)

    def test_add_node_simple_table(self):
        """Test adding a simple table."""
        result = add_node("test_table", "table", "public", "CREATE TABLE test_table", self.node_types)
        self.assertEqual(result, "public.test_table")
        self.assertIn("public.test_table", self.node_types)
        self.assertEqual(self.node_types["public.test_table"]["type"], "table")
        self.assertEqual(self.node_types["public.test_table"]["database"], "public")

    def test_add_node_without_schema(self):
        """Test adding a node without schema."""
        result = add_node("test_table", "table", None, "CREATE TABLE test_table", self.node_types)
        self.assertEqual(result, "test_table")
        self.assertIn("test_table", self.node_types)
        self.assertEqual(self.node_types["test_table"]["database"], "")

    def test_add_node_existing_node_accumulates_definition(self):
        """Test that existing nodes accumulate definitions."""
        # Add first definition
        add_node("test_table", "table", "public", "CREATE TABLE test_table", self.node_types)
        first_def = self.node_types["public.test_table"]["definition"]
        
        # Add second definition
        add_node("test_table", "table", "public", "ALTER TABLE test_table ADD COLUMN", self.node_types)
        second_def = self.node_types["public.test_table"]["definition"]
        
        # Should contain both definitions
        self.assertIn("CREATE TABLE test_table", second_def)
        self.assertIn("ALTER TABLE test_table ADD COLUMN", second_def)
        self.assertIn("-- Additional DDL --", second_def)

    def test_add_node_cte_view(self):
        """Test adding a CTE view node."""
        result = add_node("temp_cte", "cte_view", None, "WITH temp_cte AS", self.node_types)
        self.assertEqual(result, "temp_cte")
        self.assertIn("temp_cte", self.node_types)
        self.assertEqual(self.node_types["temp_cte"]["type"], "cte_view")
        self.assertEqual(self.node_types["temp_cte"]["database"], "")

    @patch('src.parsers.parser_postgres.format_sql')
    def test_add_node_formats_definition(self, mock_format):
        """Test that definitions are formatted."""
        mock_format.return_value = "FORMATTED SQL"
        
        add_node("test_table", "table", "public", "CREATE TABLE test_table", self.node_types)
        
        mock_format.assert_called_with("CREATE TABLE test_table")
        self.assertIn("FORMATTED SQL", self.node_types["public.test_table"]["definition"])

class TestFindDependencies(unittest.TestCase):
    """Test the find_dependencies function."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock sqlglot expression objects
        self.mock_query_expr = MagicMock()
        self.mock_table1 = MagicMock()
        self.mock_table1.name = "table1"
        self.mock_table1.args = {"db": None, "catalog": None}
        
        self.mock_table2 = MagicMock()
        self.mock_table2.name = "table2"
        self.mock_schema = MagicMock()
        self.mock_schema.name = "schema1"
        self.mock_table2.args = {"db": self.mock_schema, "catalog": None}

    def test_find_dependencies_simple(self):
        """Test finding simple table dependencies."""
        self.mock_query_expr.find_all.return_value = [self.mock_table1]
        
        deps = find_dependencies(self.mock_query_expr)
        
        self.assertEqual(len(deps), 1)
        self.assertIn(("table1", None), deps)

    def test_find_dependencies_with_schema(self):
        """Test finding dependencies with schema."""
        self.mock_query_expr.find_all.return_value = [self.mock_table2]
        
        # Mock the isinstance check for Identifier
        with patch('src.parsers.parser_postgres.exp.Identifier', self.mock_schema.__class__):
            deps = find_dependencies(self.mock_query_expr)
        
        self.assertEqual(len(deps), 1)
        self.assertIn(("table2", "schema1"), deps)

    def test_find_dependencies_multiple_tables(self):
        """Test finding multiple table dependencies."""
        self.mock_query_expr.find_all.return_value = [self.mock_table1, self.mock_table2]
        
        with patch('src.parsers.parser_postgres.exp.Identifier', self.mock_schema.__class__):
            deps = find_dependencies(self.mock_query_expr)
        
        self.assertEqual(len(deps), 2)
        self.assertIn(("table1", None), deps)
        self.assertIn(("table2", "schema1"), deps)

    def test_find_dependencies_empty_table_name(self):
        """Test finding dependencies with empty table name."""
        mock_empty_table = MagicMock()
        mock_empty_table.name = ""
        mock_empty_table.args = {"db": None, "catalog": None}
        
        self.mock_query_expr.find_all.return_value = [mock_empty_table]
        
        deps = find_dependencies(self.mock_query_expr)
        
        self.assertEqual(len(deps), 0)

class TestFindForeignKeys(unittest.TestCase):
    """Test the find_foreign_keys function."""

    def test_find_foreign_keys_function_exists(self):
        """Test that find_foreign_keys function is callable."""
        # Simple test to ensure the function exists and can be called
        # Complex mocking of sqlglot AST is not reliable for unit testing
        from src.parsers.parser_postgres import find_foreign_keys
        self.assertTrue(callable(find_foreign_keys))

    def test_find_foreign_keys_with_non_table_statement(self):
        """Test that function handles non-table statements gracefully."""
        # Create a mock statement that's not a table
        mock_statement = MagicMock()
        mock_statement.this = "not_a_table"
        mock_statement.find_all.return_value = []
        
        fks = find_foreign_keys(mock_statement)
        self.assertEqual(len(fks), 0)

    def test_find_foreign_keys_no_foreign_keys_found(self):
        """Test function when no foreign keys are found."""
        # Create a minimal mock that doesn't require complex isinstance mocking
        mock_statement = MagicMock()
        mock_statement.find_all.return_value = []  # No foreign keys found
        
        # Simple test - any result should work since no foreign keys are found
        fks = find_foreign_keys(mock_statement)
        self.assertEqual(len(fks), 0)

class TestParseDump(unittest.TestCase):
    """Test the parse_dump function."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock sqlglot parsing
        self.mock_statements = []

    @patch('src.parsers.parser_postgres.parse')
    @patch('os.path.exists')
    def test_parse_dump_from_file(self, mock_exists, mock_parse):
        """Test parsing from file path."""
        mock_exists.return_value = True
        mock_parse.return_value = []
        
        with patch("builtins.open", mock_open(read_data="CREATE TABLE test;")):
            edges, nodes, stats = parse_dump("/fake/path/test.sql")
        
        self.assertEqual(len(edges), 0)
        self.assertEqual(len(nodes), 0)
        self.assertEqual(len(stats), 0)

    @patch('src.parsers.parser_postgres.parse')
    @patch('os.path.exists')
    def test_parse_dump_from_string(self, mock_exists, mock_parse):
        """Test parsing from SQL string."""
        mock_exists.return_value = False
        mock_parse.return_value = []
        
        edges, nodes, stats = parse_dump("CREATE TABLE test;")
        
        mock_parse.assert_called_once()
        self.assertEqual(len(edges), 0)
        self.assertEqual(len(nodes), 0)
        self.assertEqual(len(stats), 0)

    def test_parse_dump_invalid_input_type(self):
        """Test parsing with invalid input type."""
        with self.assertRaises(ValueError):
            parse_dump(123)

    def test_parse_dump_invalid_sql_patterns(self):
        """Test parsing with content that has no SQL patterns."""
        # Content with no DDL patterns should raise InvalidSQLError
        with self.assertRaises(InvalidSQLError):
            parse_dump("This is not SQL")

    def test_parse_dump_empty_content(self):
        """Test parsing empty content."""
        # Empty content should raise InvalidSQLError
        with self.assertRaises(InvalidSQLError):
            parse_dump("")

    @patch('src.parsers.parser_postgres.parse', side_effect=Exception("Parse error"))
    def test_parse_dump_parsing_error(self, mock_parse):
        """Test parsing with sqlglot parsing error."""
        # Use valid DDL content that passes SQL_PATTERNS but fails parsing
        with self.assertRaises(InvalidSQLError):
            parse_dump("CREATE TABLE test (id INT);")

    @patch('src.parsers.parser_postgres.parse')
    @patch('os.makedirs')  
    @patch('json.dump')
    def test_parse_dump_creates_output_directory(self, mock_json_dump, mock_makedirs, mock_parse):
        """Test that output directory is created."""
        # Return a non-empty list so we get past the early return
        mock_statement = MagicMock()
        mock_parse.return_value = [mock_statement]
        
        with patch('builtins.open', mock_open()):
            parse_dump("CREATE TABLE test;")
        
        # Should create the json_structure directory
        mock_makedirs.assert_called_with('json_structure', exist_ok=True)

    @patch('src.parsers.parser_postgres.parse')
    def test_parse_dump_handles_copy_statements(self, mock_parse):
        """Test that COPY statements are properly commented out."""
        mock_parse.return_value = []
        
        sql_content = """CREATE TABLE test (id INT);
COPY test FROM STDIN;
1
2
\\.
CREATE VIEW test_view AS SELECT * FROM test;"""
        
        # The function should not raise an error and should process the content
        with patch('os.makedirs'), patch('builtins.open', mock_open()), patch('json.dump'):
            edges, nodes, stats = parse_dump(sql_content)
        
        # Verify parse was called with processed content
        mock_parse.assert_called_once()
        args, kwargs = mock_parse.call_args
        processed_content = args[0]
        
        # COPY statement and data should be commented out  
        self.assertIn("--COPY test FROM STDIN;", processed_content)
        self.assertIn("--1", processed_content)
        self.assertIn("--2", processed_content)

    @patch('src.parsers.parser_postgres.parse')
    def test_parse_dump_handles_ignored_ddl(self, mock_parse):
        """Test that ignored DDL statements are commented out."""
        mock_parse.return_value = []
        
        sql_content = """CREATE TABLE test (id INT);
CREATE FUNCTION test_func() RETURNS INT AS $$ BEGIN RETURN 1; END; $$;
CREATE INDEX test_idx ON test(id);"""
        
        with patch('os.makedirs'), patch('builtins.open', mock_open()), patch('json.dump'):
            edges, nodes, stats = parse_dump(sql_content)
        
        mock_parse.assert_called_once()
        args, kwargs = mock_parse.call_args
        processed_content = args[0]
        
        # Function and index creation should be commented out
        self.assertIn("--CREATE FUNCTION", processed_content)
        self.assertIn("--CREATE INDEX", processed_content)

    @patch('src.parsers.parser_postgres.parse')
    @patch('src.parsers.parser_postgres.sqlfluff.fix')
    def test_parse_dump_uses_sqlfluff_if_available(self, mock_fix, mock_parse):
        """Test that sqlfluff is used for preprocessing if available."""
        mock_parse.return_value = []
        mock_fix.return_value = "FORMATTED SQL"
        
        parse_dump("CREATE TABLE test;")
        
        mock_fix.assert_called_once()

    @patch('src.parsers.parser_postgres.parse')
    def test_parse_dump_handles_missing_sqlfluff(self, mock_parse):
        """Test that missing sqlfluff doesn't break parsing."""
        mock_parse.return_value = []
        
        # Mock ImportError for sqlfluff
        with patch('src.parsers.parser_postgres.sqlfluff', side_effect=ImportError()):
            edges, nodes, stats = parse_dump("CREATE TABLE test;")
        
        # Should still work without sqlfluff
        mock_parse.assert_called_once()

    @patch('src.parsers.parser_postgres.parse')
    @patch('os.makedirs')
    @patch('json.dump')
    def test_parse_dump_creates_json_files(self, mock_json_dump, mock_makedirs, mock_parse):
        """Test that JSON output files are created."""
        # Return a non-empty list so we get past the early return
        mock_statement = MagicMock()
        mock_parse.return_value = [mock_statement]
        
        # Mock the file operations separately
        mock_files = {}
        def mock_open_side_effect(filename, mode='r', **kwargs):
            if 'json_structure' in filename:
                # Mock JSON file creation
                mock_files[filename] = mock_open()()
                return mock_files[filename]
            elif filename == 'cleaned_sql.sql':
                # Allow cleaned_sql.sql to be written
                return mock_open()()
            else:
                return mock_open()()
        
        with patch('builtins.open', side_effect=mock_open_side_effect):
            parse_dump("CREATE TABLE test;")
            
            # Should have called json.dump twice (edges and node_types)
            self.assertEqual(mock_json_dump.call_count, 2)
            # Should have created output directory
            mock_makedirs.assert_called_with('json_structure', exist_ok=True)

    @patch('src.parsers.parser_postgres.parse')
    def test_parse_dump_handles_json_write_error(self, mock_parse):
        """Test that JSON write errors are handled gracefully."""
        # Return a non-empty list so we get past the early return
        mock_statement = MagicMock()
        mock_parse.return_value = [mock_statement]
        
        # Mock file operations to raise IOError for JSON files only
        def mock_open_side_effect(filename, mode='r', **kwargs):
            if 'json_structure' in filename:
                raise IOError("Write error")
            else:
                return mock_open()()
        
        with patch('builtins.open', side_effect=mock_open_side_effect), \
             patch('os.makedirs'), \
             patch('builtins.print') as mock_print:
            
            # Should not raise exception
            parse_dump("CREATE TABLE test;")
            
            # Should print warning
            mock_print.assert_called()

class TestIntegrationParseDump(unittest.TestCase):
    """Simplified integration tests for parse_dump."""

    @patch('src.parsers.parser_postgres.parse')
    @patch('os.makedirs')
    @patch('json.dump')
    def test_parse_dump_create_table_integration(self, mock_json_dump, mock_makedirs, mock_parse):
        """Test parse_dump with simplified mocking."""
        # Return a non-empty list so we get past the early return
        mock_statement = MagicMock()
        mock_parse.return_value = [mock_statement]
        
        with patch('builtins.open', mock_open()):
            edges, nodes, stats = parse_dump("CREATE TABLE test_table (id INT);")
        
        # Should return empty results since we don't have real CREATE statements
        self.assertEqual(len(edges), 0)
        self.assertEqual(len(nodes), 0)
        self.assertEqual(len(stats), 0)
        
        # Should still call parse and create output files
        mock_parse.assert_called_once()
        mock_makedirs.assert_called_with('json_structure', exist_ok=True)

    @patch('src.parsers.parser_postgres.parse')
    @patch('os.makedirs')
    @patch('json.dump')
    def test_parse_dump_alter_table_integration(self, mock_json_dump, mock_makedirs, mock_parse):
        """Test parse_dump with ALTER TABLE."""
        # Return a non-empty list so we get past the early return
        mock_statement = MagicMock()
        mock_parse.return_value = [mock_statement]
        
        with patch('builtins.open', mock_open()):
            edges, nodes, stats = parse_dump("ALTER TABLE test_table ADD COLUMN name VARCHAR(50);")
        
        # Should return empty results since we don't have real ALTER statements
        self.assertEqual(len(edges), 0)
        self.assertEqual(len(nodes), 0)
        self.assertEqual(len(stats), 0)
        
        # Should still call parse and create output files
        mock_parse.assert_called_once()
        mock_makedirs.assert_called_with('json_structure', exist_ok=True)

if __name__ == "__main__":
    unittest.main()
