import unittest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from src import pyvis_mod


class TestPyvisIntegration(unittest.TestCase):
    """Test the pyvis HTML generation and browser integration"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()

        # Sample data for testing
        self.edges = [("table1", "view1"), ("table2", "view1")]
        self.node_types = {
            "table1": {"type": "table", "database": "db1", "full_name": "db1.table1"},
            "table2": {"type": "table", "database": "db2", "full_name": "db2.table2"},
            "view1": {"type": "view", "database": "db1", "full_name": "db1.view1"},
        }

    def test_html_generation(self):
        """Test that HTML file is generated correctly"""
        # Generate HTML without auto_open
        pyvis_mod.draw_pyvis_html(
            self.edges,
            self.node_types,
            save_path=self.temp_dir,
            file_name="test",
            auto_open=False,
        )

        # Check if file was created
        html_file = os.path.join(self.temp_dir, "data_flow_pyvis_test.html")
        self.assertTrue(os.path.exists(html_file))

        # Verify basic content
        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("<html>", content)
            self.assertIn("vis-network", content)
            self.assertIn("mynetwork", content)

    @patch("webbrowser.open")
    def test_auto_open_feature(self, mock_open):
        """Test auto_open feature for browser integration"""
        # Generate HTML with auto_open=True
        pyvis_mod.draw_pyvis_html(
            self.edges,
            self.node_types,
            save_path=self.temp_dir,
            file_name="auto_open_test",
            auto_open=True,
        )

        # Check if browser open was called
        mock_open.assert_called_once()

        # The URL should start with file:// and contain the file name
        url = mock_open.call_args[0][0]
        self.assertTrue(url.startswith("file://"))
        self.assertIn("data_flow_pyvis_auto_open_test.html", url)

    @patch("webbrowser.open")
    def test_auto_open_disabled(self, mock_open):
        """Test auto_open disabled doesn't open browser"""
        # Generate HTML with auto_open=False
        pyvis_mod.draw_pyvis_html(
            self.edges,
            self.node_types,
            save_path=self.temp_dir,
            file_name="no_auto_open_test",
            auto_open=False,
        )

        # Check that browser open was NOT called
        mock_open.assert_not_called()

    def test_focused_view_vs_complete_view(self):
        """Test differences between focused and complete view generation"""
        # Generate complete view
        pyvis_mod.draw_pyvis_html(
            self.edges,
            self.node_types,
            save_path=self.temp_dir,
            file_name="complete",
            auto_open=False,
            is_focused_view=False,
        )

        # Generate focused view
        pyvis_mod.draw_pyvis_html(
            self.edges,
            self.node_types,
            save_path=self.temp_dir,
            file_name="focused",
            auto_open=False,
            focus_nodes=["view1"],
            is_focused_view=True,
        )

        # Check that both files were created with correct names
        complete_file = os.path.join(self.temp_dir, "data_flow_pyvis_complete.html")
        focused_file = os.path.join(
            self.temp_dir, "focused_data_flow_pyvis_focused.html"
        )

        self.assertTrue(os.path.exists(complete_file))
        self.assertTrue(os.path.exists(focused_file))

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)


if __name__ == "__main__":
    unittest.main()
