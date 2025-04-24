import unittest
import os
import shutil
from src.generate_data_flow import (
    parse_dump,
    draw_complete_data_flow,
    draw_focused_data_flow,
)


class TestEndToEnd(unittest.TestCase):
    """Integration tests for complete data flow generation process"""

    def setUp(self):
        """Set up test environment and sample data"""
        self.test_dir = "test_output"
        if not os.path.exists(self.test_dir):
            os.makedirs(self.test_dir)

        # Sample VQL with multiple dependencies
        self.sample_vql = """
        CREATE OR REPLACE VIEW db1.summary_view AS
        SELECT * FROM db2.source_table
        JOIN db3.lookup_table ON source_table.id = lookup_table.id;

        CREATE OR REPLACE TABLE db1.aggregated_data
        DATA_LOAD_QUERY = '
            SELECT 
                t1.id,
                t2.name,
                t3.value
            FROM db2.table1 t1
            JOIN db3.table2 t2 ON t1.id = t2.id
            LEFT JOIN db4.table3 t3 ON t1.id = t3.id
            WHERE t1.active = true
        ';

        CREATE OR REPLACE VIEW db1.final_view AS
        SELECT * FROM db1.summary_view
        UNION ALL
        SELECT * FROM db1.aggregated_data;
        """

        self.test_file = os.path.join(self.test_dir, "test.vql")
        with open(self.test_file, "w") as f:
            f.write(self.sample_vql)

    def test_complete_workflow(self):
        """Test the complete workflow from parsing to visualization"""
        # 1. Parse VQL content
        edges, node_types, db_stats = parse_dump(self.test_file)

        # Verify parsing results
        self.assertTrue(edges, "Edges should not be empty")
        self.assertTrue(node_types, "Node types should not be empty")
        self.assertTrue(db_stats, "Database stats should not be empty")

        # Check specific node types and databases
        self.assertEqual(node_types["summary_view"]["type"], "view")
        self.assertEqual(node_types["summary_view"]["database"], "db1")
        self.assertEqual(node_types["source_table"]["type"], "table")
        self.assertEqual(node_types["source_table"]["database"], "db2")

        # 2. Generate complete data flow visualization
        complete_html = os.path.join(self.test_dir, "data_flow_pyvis_test.html")
        draw_complete_data_flow(
            edges,
            node_types,
            save_path=self.test_dir,
            auto_open=False,
            file_name="test",
        )
        self.assertTrue(
            os.path.exists(complete_html), "Complete flow HTML should be generated"
        )

        # 3. Generate focused data flow visualization
        focused_html = os.path.join(self.test_dir, "focused_data_flow_pyvis_test.html")

        # Make sure we're using a node that actually exists in the graph
        # Use one of the nodes we know exists from our sample VQL
        valid_focus_nodes = [node for node in node_types.keys()]
        self.assertTrue(len(valid_focus_nodes) > 0, "No valid nodes found for focus")

        draw_focused_data_flow(
            edges,
            node_types,
            focus_nodes=valid_focus_nodes[:1],  # Use the first valid node
            auto_open=False,
            save_path=self.test_dir,
            file_name="test",
        )
        self.assertTrue(
            os.path.exists(focused_html), "Focused flow HTML should be generated"
        )

        # 4. Verify HTML content
        def verify_html_content(file_path):
            with open(file_path, "r", encoding="utf-8") as f:  # Specify encoding
                content = f.read()
                # Check for key HTML elements only - HTML and vis components
                self.assertIn("<html", content.lower())
                self.assertIn("<body", content.lower())
                self.assertIn("vis-network", content.lower())

        verify_html_content(complete_html)
        verify_html_content(focused_html)

    def test_error_handling(self):
        """Test error handling in the workflow"""
        # Test with invalid SQL
        invalid_file = os.path.join(self.test_dir, "invalid.vql")
        with open(invalid_file, "w") as f:
            f.write("This is not valid SQL")

        with self.assertRaises(Exception):
            parse_dump(invalid_file)

        # Test with nonexistent focus nodes
        edges, node_types, _ = parse_dump(self.test_file)
        draw_focused_data_flow(
            edges,
            node_types,
            focus_nodes=["nonexistent_view"],
            auto_open=False,
            save_path=self.test_dir,
            file_name="test_error",
        )
        # Should not generate file for invalid focus nodes
        self.assertFalse(
            os.path.exists(
                os.path.join(self.test_dir, "focused_data_flow_test_error.html")
            )
        )

    def test_output_file_validation(self):
        """Test the validity of generated output files"""
        # Generate visualizations
        edges, node_types, _ = parse_dump(self.test_file)
        draw_complete_data_flow(
            edges,
            node_types,
            save_path=self.test_dir,
            auto_open=False,
            file_name="test",
        )

        # Check complete flow HTML
        html_file = os.path.join(self.test_dir, "data_flow_pyvis_test.html")
        self.assertTrue(os.path.exists(html_file))

        # Verify file size is reasonable (not empty, not too large)
        size = os.path.getsize(html_file)
        self.assertGreater(size, 1000, "HTML file seems too small")
        self.assertLess(size, 10000000, "HTML file seems too large")

        # Verify basic HTML structure and required scripts
        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()
            # self.assertIn("<!DOCTYPE html>", content)
            self.assertIn("<html>", content)
            self.assertIn("<head>", content)
            self.assertIn("<body>", content)
            self.assertIn("vis-network", content)
            self.assertIn("</html>", content)
            self.assertIn("mynetwork", content)

    def test_file_path_normalization(self):
        """Test file path normalization for cross-platform compatibility"""
        from src.dataflow import normalize_file_path, normalize_path_for_platform

        # Test basic path normalization
        windows_path = r"C:\Users\test\file.sql"
        unix_path = "/home/user/file.sql"

        # These should not raise errors on any platform
        norm_win = normalize_file_path(windows_path)
        norm_unix = normalize_file_path(unix_path)

        # Test handling of file:// URLs
        file_url = "file:///C:/Users/test/file.sql"
        norm_url = normalize_file_path(file_url)
        self.assertNotIn("file://", norm_url)

        # Test platform-specific normalization
        platform_norm = normalize_path_for_platform(windows_path)
        self.assertIsInstance(platform_norm, str)
        self.assertTrue(len(platform_norm) > 0)

    def test_browser_open_parameter(self):
        """Test that the auto_open parameter is correctly passed and handled"""
        from unittest.mock import patch

        # Patch webbrowser.open to avoid actually opening a browser during tests
        with patch("webbrowser.open") as mock_open:
            # Generate graph with auto_open=True
            edges, node_types, _ = parse_dump(self.test_file)

            # Test with auto_open=True (should call webbrowser.open)
            draw_complete_data_flow(
                edges,
                node_types,
                save_path=self.test_dir,
                file_name="test_browser",
                auto_open=True,
            )

            # Verify webbrowser.open was called
            mock_open.assert_called_once()

    def tearDown(self):
        """Clean up test directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)


if __name__ == "__main__":
    unittest.main()
