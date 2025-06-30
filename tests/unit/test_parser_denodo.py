"""
Comprehensive tests for the Denodo parser module.
Tests cover all major functions and edge cases.
"""
import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import tempfile
from typing import Dict, List, Tuple

# Import the module under test
from src.parsers.parser_denodo import (
    find_script_dependencies,
    add_node,
    guess_type,
    parse_dump,
    database_stats,
    node_types,
    edges,
    db_objects
)
from src.dataflow_structs import NodeInfo
from src.exceptions import InvalidSQLError


class TestFindScriptDependencies(unittest.TestCase):
    """Test the find_script_dependencies function."""

    def setUp(self):
        """Set up test fixtures."""
        self.empty_node_types = {}
        self.empty_db_objects = {}
        
        self.sample_node_types = {
            "test_table": {
                "type": "table",
                "database": "db1",
                "full_name": "db1.test_table",
                "definition": None
            },
            "test_view": {
                "type": "view", 
                "database": "db1",
                "full_name": "db1.test_view",
                "definition": None
            },
            "cte_temp": {
                "type": "cte_view",
                "database": "",
                "full_name": "cte_temp",
                "definition": None
            }
        }
        
        self.sample_db_objects = {
            "db1": {
                "test_table": {
                    "full_name": "db1.test_table",
                    "type": "table",
                    "is_dependency": False
                }
            }
        }

    def test_find_dependencies_simple_from(self):
        """Test finding dependencies from simple FROM clause."""
        sql = "SELECT * FROM test_table"
        deps = find_script_dependencies(sql, self.empty_node_types, self.empty_db_objects)
        self.assertIn("test_table", deps)

    def test_find_dependencies_with_join(self):
        """Test finding dependencies with JOIN clauses."""
        sql = "SELECT * FROM table1 t1 JOIN table2 t2 ON t1.id = t2.id"
        deps = find_script_dependencies(sql, self.empty_node_types, self.empty_db_objects)
        self.assertIn("table1", deps)
        self.assertIn("table2", deps)

    def test_find_dependencies_with_schema(self):
        """Test finding dependencies with schema-qualified names."""
        sql = "SELECT * FROM schema1.table1 JOIN schema2.table2"
        deps = find_script_dependencies(sql, self.empty_node_types, self.empty_db_objects)
        self.assertIn("schema1.table1", deps)
        self.assertIn("schema2.table2", deps)

    def test_find_dependencies_with_implementation(self):
        """Test finding dependencies from SET IMPLEMENTATION."""
        sql = "SET IMPLEMENTATION impl_table"
        deps = find_script_dependencies(sql, self.empty_node_types, self.empty_db_objects)
        self.assertIn("impl_table", deps)

    def test_find_dependencies_with_description_sources(self):
        """Test finding dependencies from DESCRIPTION sources."""
        sql = "DESCRIPTION = 'This view uses source>>source_table<<source'"
        deps = find_script_dependencies(sql, self.empty_node_types, self.empty_db_objects)
        self.assertIn("source_table", deps)

    def test_find_dependencies_removes_comments(self):
        """Test that comments are properly removed before parsing."""
        sql = """
        SELECT * FROM table1 -- This is a comment
        /* This is a block comment */
        JOIN table2
        """
        deps = find_script_dependencies(sql, self.empty_node_types, self.empty_db_objects)
        self.assertIn("table1", deps)
        self.assertIn("table2", deps)

    def test_find_dependencies_with_node_types_context(self):
        """Test dependency resolution using node_types context."""
        sql = "SELECT * FROM test_table"
        deps = find_script_dependencies(sql, self.sample_node_types, self.sample_db_objects)
        self.assertIn("db1.test_table", deps)

    def test_find_dependencies_excludes_cte(self):
        """Test that CTE views don't get database prefixed."""
        sql = "SELECT * FROM cte_temp"
        deps = find_script_dependencies(sql, self.sample_node_types, self.sample_db_objects)
        self.assertIn("cte_temp", deps)

    def test_find_dependencies_empty_sql(self):
        """Test with empty SQL."""
        deps = find_script_dependencies("", self.empty_node_types, self.empty_db_objects)
        self.assertEqual(deps, [])

    def test_find_dependencies_no_tables(self):
        """Test SQL with no table references."""
        sql = "SELECT 1 as test_column"
        deps = find_script_dependencies(sql, self.empty_node_types, self.empty_db_objects)
        self.assertEqual(deps, [])


class TestAddNode(unittest.TestCase):
    """Test the add_node function."""

    def setUp(self):
        """Set up test fixtures - reset global state."""
        # Import and reset the global variables from the module
        import src.parsers.parser_denodo as denodo_module
        denodo_module.node_types.clear()
        denodo_module.db_objects.clear()

    def tearDown(self):
        """Clean up after each test."""
        # Clean up the global variables from the module
        import src.parsers.parser_denodo as denodo_module
        denodo_module.node_types.clear()
        denodo_module.db_objects.clear()

    def test_add_node_simple_table(self):
        """Test adding a simple table node."""
        result = add_node("test_table", "table", False, "CREATE TABLE test_table")
        import src.parsers.parser_denodo as denodo_module
        self.assertEqual(result, "test_table")
        self.assertIn("test_table", denodo_module.node_types)
        self.assertEqual(denodo_module.node_types["test_table"]["type"], "table")

    def test_add_node_with_database(self):
        """Test adding a node with database qualification."""
        result = add_node("db1.test_table", "table", False, "CREATE TABLE db1.test_table")
        import src.parsers.parser_denodo as denodo_module
        self.assertEqual(result, "test_table")
        self.assertEqual(denodo_module.node_types["test_table"]["database"], "db1")
        self.assertEqual(denodo_module.node_types["test_table"]["full_name"], "db1.test_table")

    def test_add_node_cte_view(self):
        """Test adding a CTE view node."""
        result = add_node("temp_cte", "cte_view", False, None)
        import src.parsers.parser_denodo as denodo_module
        self.assertEqual(result, "temp_cte")
        self.assertEqual(denodo_module.node_types["temp_cte"]["type"], "cte_view")
        self.assertEqual(denodo_module.node_types["temp_cte"]["database"], "")
        self.assertEqual(denodo_module.node_types["temp_cte"]["full_name"], "temp_cte")

    def test_add_node_existing_node_type_priority(self):
        """Test type priority when updating existing nodes."""
        import src.parsers.parser_denodo as denodo_module
        # Add as table first
        add_node("test_obj", "table", False, None)
        self.assertEqual(denodo_module.node_types["test_obj"]["type"], "table")
        
        # Update to view (higher priority)
        add_node("test_obj", "view", False, None)
        self.assertEqual(denodo_module.node_types["test_obj"]["type"], "view")
        
        # Try to downgrade to table (should not change)
        add_node("test_obj", "table", False, None)
        self.assertEqual(denodo_module.node_types["test_obj"]["type"], "view")

    def test_add_node_cte_priority(self):
        """Test that CTE type has ultimate priority."""
        import src.parsers.parser_denodo as denodo_module
        # Start with table
        add_node("test_obj", "table", False, None)
        self.assertEqual(denodo_module.node_types["test_obj"]["type"], "table")
        
        # Convert to CTE (should override)
        add_node("test_obj", "cte_view", False, None)
        self.assertEqual(denodo_module.node_types["test_obj"]["type"], "cte_view")
        self.assertEqual(denodo_module.node_types["test_obj"]["database"], "")
        
        # Try to change from CTE (should not work)
        add_node("test_obj", "view", False, None)
        self.assertEqual(denodo_module.node_types["test_obj"]["type"], "cte_view")

    def test_add_node_empty_name(self):
        """Test adding node with empty name."""
        import src.parsers.parser_denodo as denodo_module
        result = add_node("", "table", False, None)
        self.assertEqual(result, "")
        self.assertEqual(len(denodo_module.node_types), 0)

    def test_add_node_dependency_vs_non_dependency(self):
        """Test handling of dependency vs non-dependency nodes."""
        import src.parsers.parser_denodo as denodo_module
        # Add as dependency first
        add_node("test_table", "table", True, None)
        self.assertIsNone(denodo_module.node_types["test_table"]["definition"])
        
        # Add as non-dependency with definition
        add_node("test_table", "table", False, "CREATE TABLE test_table")
        self.assertIsNotNone(denodo_module.node_types["test_table"]["definition"])

    def test_add_node_updates_db_objects(self):
        """Test that db_objects is properly updated."""
        import src.parsers.parser_denodo as denodo_module
        add_node("db1.test_table", "table", False, None)
        self.assertIn("db1", denodo_module.db_objects)
        self.assertIn("test_table", denodo_module.db_objects["db1"])
        self.assertEqual(denodo_module.db_objects["db1"]["test_table"]["type"], "table")


class TestGuessType(unittest.TestCase):
    """Test the guess_type function."""

    def setUp(self):
        """Set up test fixtures."""
        global node_types
        node_types.clear()
        node_types["known_table"] = {
            "type": "table",
            "database": "db1", 
            "full_name": "db1.known_table",
            "definition": None
        }

    def tearDown(self):
        """Clean up after each test."""
        global node_types
        node_types.clear()

    def test_guess_type_known_node(self):
        """Test guessing type for known node."""
        result = guess_type("known_table")
        self.assertEqual(result, "table")

    def test_guess_type_view_prefixes(self):
        """Test guessing type based on view naming conventions."""
        view_names = ["v_test", "iv_test", "rv_test", "bv_test", "wv_test", "u_test"]
        for name in view_names:
            result = guess_type(name)
            self.assertEqual(result, "view", f"Failed for name: {name}")

    def test_guess_type_table_prefixes(self):
        """Test guessing type based on table naming conventions."""
        table_names = ["t_test", "it_test", "ft_test", "i_test"]
        for name in table_names:
            result = guess_type(name)
            self.assertEqual(result, "table", f"Failed for name: {name}")

    def test_guess_type_contains_view(self):
        """Test guessing type when name contains 'view'."""
        result = guess_type("customer_view")
        self.assertEqual(result, "view")

    def test_guess_type_default_table(self):
        """Test default guess is table when no patterns match."""
        result = guess_type("random_name")
        self.assertEqual(result, "table")


class TestParseDump(unittest.TestCase):
    """Test the parse_dump function."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset global state before each test
        global database_stats, node_types, edges, db_objects
        database_stats.clear()
        node_types.clear()
        edges.clear()
        db_objects.clear()

    def tearDown(self):
        """Clean up after each test."""
        global database_stats, node_types, edges, db_objects
        database_stats.clear()
        node_types.clear()
        edges.clear()
        db_objects.clear()

    def test_parse_dump_simple_view(self):
        """Test parsing a simple CREATE VIEW statement."""
        sql_content = """
        CREATE VIEW test_view AS
        SELECT * FROM source_table;
        """
        
        edges_result, nodes_result, stats_result = parse_dump(sql_content)
        
        # Check that view and source table are created
        self.assertIn("test_view", nodes_result)
        self.assertIn("source_table", nodes_result)
        self.assertEqual(nodes_result["test_view"]["type"], "view")
        
        # Check that dependency edge is created
        self.assertIn(("source_table", "test_view"), edges_result)

    def test_parse_dump_table_with_data_load_query(self):
        """Test parsing a CREATE TABLE with DATA_LOAD_QUERY."""
        sql_content = """
        CREATE TABLE test_table
        DATA_LOAD_QUERY = 'SELECT * FROM source_table';
        """
        
        edges_result, nodes_result, stats_result = parse_dump(sql_content)
        
        self.assertIn("test_table", nodes_result)
        self.assertIn("source_table", nodes_result)
        self.assertEqual(nodes_result["test_table"]["type"], "table")
        self.assertIn(("source_table", "test_table"), edges_result)

    def test_parse_dump_with_cte(self):
        """Test parsing a view with Common Table Expressions."""
        sql_content = """
        CREATE VIEW complex_view AS
        WITH temp_cte AS (
            SELECT id FROM source_table1
        ),
        another_cte AS (
            SELECT id FROM source_table2  
        )
        SELECT * FROM temp_cte JOIN another_cte USING(id);
        """
        
        edges_result, nodes_result, stats_result = parse_dump(sql_content)
        
        # Check CTE nodes are created
        self.assertIn("temp_cte", nodes_result)
        self.assertIn("another_cte", nodes_result)
        self.assertEqual(nodes_result["temp_cte"]["type"], "cte_view")
        self.assertEqual(nodes_result["another_cte"]["type"], "cte_view")
        
        # Check source tables are created
        self.assertIn("source_table1", nodes_result)
        self.assertIn("source_table2", nodes_result)
        
        # Check edges are created correctly
        self.assertIn(("source_table1", "temp_cte"), edges_result)
        self.assertIn(("source_table2", "another_cte"), edges_result)
        self.assertIn(("temp_cte", "complex_view"), edges_result)
        self.assertIn(("another_cte", "complex_view"), edges_result)

    def test_parse_dump_with_implementation(self):
        """Test parsing a view with SET IMPLEMENTATION."""
        sql_content = """
        CREATE VIEW test_view AS
        SELECT * FROM base_table
        SET IMPLEMENTATION impl_table;
        """
        
        edges_result, nodes_result, stats_result = parse_dump(sql_content)
        
        self.assertIn("test_view", nodes_result)
        self.assertIn("base_table", nodes_result)
        self.assertIn("impl_table", nodes_result)
        
        # Should have edges from both base_table and impl_table to test_view
        self.assertIn(("base_table", "test_view"), edges_result)
        self.assertIn(("impl_table", "test_view"), edges_result)

    def test_parse_dump_with_description_sources(self):
        """Test parsing with DESCRIPTION containing source references."""
        sql_content = """
        CREATE VIEW test_view AS
        SELECT * FROM base_table
        DESCRIPTION = 'This view uses source>>external_source<<source data';
        """
        
        edges_result, nodes_result, stats_result = parse_dump(sql_content)
        
        self.assertIn("test_view", nodes_result)
        self.assertIn("base_table", nodes_result)
        self.assertIn("external_source", nodes_result)
        
        self.assertIn(("base_table", "test_view"), edges_result)
        self.assertIn(("external_source", "test_view"), edges_result)

    def test_parse_dump_database_stats(self):
        """Test that database statistics are calculated correctly."""
        sql_content = """
        CREATE VIEW db1.view1 AS SELECT * FROM db1.table1;
        CREATE TABLE db1.table2 AS SELECT * FROM db2.table3;
        CREATE VIEW db2.view2 AS SELECT * FROM db2.table4;
        """
        
        edges_result, nodes_result, stats_result = parse_dump(sql_content)
        
        # Check database statistics (should count non-CTE nodes per database)
        self.assertIn("db1", stats_result)
        self.assertIn("db2", stats_result)
        # db1 should have view1, table1, table2 = 3 nodes
        # db2 should have table3, view2, table4 = 3 nodes
        self.assertTrue(stats_result["db1"] >= 2)  # At least view1 and table2
        self.assertTrue(stats_result["db2"] >= 2)  # At least view2 and dependencies

    def test_parse_dump_invalid_sql_error(self):
        """Test that InvalidSQLError is raised for invalid SQL."""
        with self.assertRaises(InvalidSQLError):
            parse_dump("This is not SQL content")

    def test_parse_dump_empty_content_error(self):
        """Test that InvalidSQLError is raised for empty content."""
        with self.assertRaises(InvalidSQLError):
            parse_dump("")

    def test_parse_dump_no_create_statements(self):
        """Test parsing content with no CREATE statements."""
        sql_content = "SELECT * FROM some_table;"
        
        edges_result, nodes_result, stats_result = parse_dump(sql_content)
        
        # Should return empty results but not error
        self.assertEqual(len(edges_result), 0)
        self.assertEqual(len(nodes_result), 0)
        self.assertEqual(len(stats_result), 0)

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open, read_data="CREATE VIEW test AS SELECT * FROM source;")
    def test_parse_dump_from_file(self, mock_file, mock_makedirs):
        """Test parsing from a file path."""
        edges_result, nodes_result, stats_result = parse_dump("/fake/path/test.sql")
        
        # Verify the file was read (but open is called multiple times for JSON output)
        file_calls = [call for call in mock_file.call_args_list if 'test.sql' in str(call)]
        self.assertTrue(len(file_calls) >= 1)
        self.assertIn("test", nodes_result)
        self.assertIn("source", nodes_result)

    @patch("os.makedirs")
    @patch("builtins.open")
    def test_parse_dump_file_not_found_fallback_to_string(self, mock_open_func, mock_makedirs):
        """Test that file not found falls back to treating input as string."""
        # Configure mock to trigger the string fallback path
        def side_effect(*args, **kwargs):
            if args[0] == "CREATE VIEW test AS SELECT * FROM source;":
                raise FileNotFoundError()  # This triggers the string fallback
            else:
                # Allow JSON file operations to work
                return mock_open()()
        
        mock_open_func.side_effect = side_effect
        sql_content = "CREATE VIEW test AS SELECT * FROM source;"
        
        edges_result, nodes_result, stats_result = parse_dump(sql_content)
        
        self.assertIn("test", nodes_result)
        self.assertIn("source", nodes_result)

    def test_parse_dump_value_error_invalid_input(self):
        """Test ValueError for invalid input types."""
        with self.assertRaises(ValueError):
            parse_dump(123)  # Invalid type

    @patch("os.path.exists")
    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_parse_dump_creates_json_output(self, mock_file, mock_makedirs, mock_exists):
        """Test that JSON output files are created."""
        mock_exists.return_value = False
        
        # Configure the mock to handle file operations properly
        # First call fails (simulating string input), subsequent calls work for JSON writing
        def file_side_effect(*args, **kwargs):
            if args[0] == "CREATE VIEW test AS SELECT * FROM source;":
                raise FileNotFoundError()  # Trigger string fallback path
            else:
                # Return a proper mock file for JSON writing
                return mock_open()()
        
        mock_file.side_effect = file_side_effect
        
        # Use valid SQL that will pass the pattern check
        sql_content = "CREATE VIEW test AS SELECT * FROM source;"
        
        parse_dump(sql_content)
        
        # Should create json_structure directory if it doesn't exist
        mock_makedirs.assert_called_once_with("json_structure")
        
        # Should have attempted to open JSON files for writing
        json_file_calls = [call for call in mock_file.call_args_list 
                          if 'json_structure' in str(call)]
        self.assertTrue(len(json_file_calls) >= 2)  # At least edges.json and node_types.json

    def test_parse_dump_comments_removed(self):
        """Test that comments are properly removed from statements."""
        sql_content = """
        CREATE VIEW test_view AS -- line comment
        /* block comment */
        SELECT * FROM source_table; -- another comment
        """
        
        edges_result, nodes_result, stats_result = parse_dump(sql_content)
        
        self.assertIn("test_view", nodes_result)
        self.assertIn("source_table", nodes_result)

    def test_parse_dump_schema_qualified_names(self):
        """Test parsing with schema-qualified object names."""
        sql_content = """
        CREATE VIEW schema1.view1 AS
        SELECT * FROM schema2.table1 JOIN schema1.table2;
        """
        
        edges_result, nodes_result, stats_result = parse_dump(sql_content)
        
        # Check that nodes are created with correct names
        self.assertIn("view1", nodes_result)
        self.assertIn("table1", nodes_result) 
        self.assertIn("table2", nodes_result)
        
        # Check full names are preserved
        self.assertEqual(nodes_result["view1"]["full_name"], "schema1.view1")
        self.assertEqual(nodes_result["view1"]["database"], "schema1")


class TestGlobalStateReset(unittest.TestCase):
    """Test that global state is properly reset between parse_dump calls."""
    
    def test_global_state_reset(self):
        """Test that globals are reset between parse calls."""
        # First parse
        sql1 = "CREATE VIEW view1 AS SELECT * FROM table1;"
        edges1, nodes1, stats1 = parse_dump(sql1)
        
        # Check first parse results
        self.assertIn("view1", nodes1)
        self.assertIn("table1", nodes1)
        
        # Second parse with different content
        sql2 = "CREATE VIEW view2 AS SELECT * FROM table2;"
        edges2, nodes2, stats2 = parse_dump(sql2)
        
        # Check that second parse doesn't contain first parse data
        self.assertNotIn("view1", nodes2)
        self.assertNotIn("table1", nodes2)
        self.assertIn("view2", nodes2)
        self.assertIn("table2", nodes2)


if __name__ == "__main__":
    unittest.main()
