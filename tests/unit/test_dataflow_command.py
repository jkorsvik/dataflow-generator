import os
import sys
import tempfile
import shutil
import pytest
from src import dataflow_command
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from io import StringIO


def create_temp_vql(content=None):
    if content is None:
        # Use at least two nodes and one edge to avoid ZeroDivisionError
        content = """
        CREATE OR REPLACE TABLE t1 AS SELECT 1;
        CREATE OR REPLACE VIEW v_test AS SELECT * FROM t1;
        """
    fd, path = tempfile.mkstemp(suffix=".vql")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    return path


def test_complete_diagram(monkeypatch):
    vql_path = create_temp_vql()
    out_dir = tempfile.mkdtemp()
    sys_argv = ["prog", "--metadata", vql_path, "--output", out_dir]
    monkeypatch.setattr(sys, "argv", sys_argv)
    dataflow_command.main()
    # Check output file exists
    files = os.listdir(out_dir)
    assert any(f.endswith(".html") for f in files)
    shutil.rmtree(out_dir)
    os.remove(vql_path)


def test_focused_diagram(monkeypatch):
    vql_path = create_temp_vql()
    out_dir = tempfile.mkdtemp()
    sys_argv = [
        "prog",
        "--metadata",
        vql_path,
        "--type",
        "focused",
        "--focus-nodes",
        "v_test",
        "--output",
        out_dir,
    ]
    monkeypatch.setattr(sys, "argv", sys_argv)
    dataflow_command.main()
    files = os.listdir(out_dir)
    assert any(f.endswith(".html") for f in files)
    shutil.rmtree(out_dir)
    os.remove(vql_path)


def test_missing_focus_nodes(monkeypatch):
    vql_path = create_temp_vql()
    sys_argv = ["prog", "--metadata", vql_path, "--type", "focused"]
    monkeypatch.setattr(sys, "argv", sys_argv)
    with pytest.raises(SystemExit):
        dataflow_command.main()
    os.remove(vql_path)


def test_main_db(monkeypatch):
    vql_path = create_temp_vql("""CREATE OR REPLACE VIEW db1.v_test AS SELECT 1;""")
    out_dir = tempfile.mkdtemp()
    sys_argv = ["prog", "--metadata", vql_path, "--main-db", "db1", "--output", out_dir]
    monkeypatch.setattr(sys, "argv", sys_argv)
    dataflow_command.main()
    files = os.listdir(out_dir)
    assert any(f.endswith(".html") for f in files)
    shutil.rmtree(out_dir)
    os.remove(vql_path)


class TestDataflowCommand(unittest.TestCase):
    """Test the dataflow command-line interface"""

    def setUp(self):
        """Set up test environment"""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()

        # Create a sample VQL file for testing
        self.sample_vql = """
        CREATE OR REPLACE VIEW db1.test_view AS
        SELECT * FROM db2.test_table1
        JOIN db1.test_table2 ON test_table1.id = test_table2.id;
        """

        self.test_file = os.path.join(self.temp_dir, "test.vql")
        with open(self.test_file, "w") as f:
            f.write(self.sample_vql)

    @patch("sys.argv")
    @patch("src.dataflow_command.draw_complete_data_flow")
    @patch("argparse.ArgumentParser.parse_args")
    def test_command_interface_complete_auto_open(
        self, mock_parse_args, mock_draw, mock_argv
    ):
        """Test auto_open parameter for complete flow diagram"""
        # Mock the argument parser to return auto_open=True
        import argparse

        mock_args = argparse.Namespace(
            metadata=self.test_file,
            type="complete",
            output=self.temp_dir,
            auto_open=True,  # Set auto_open to True (default)
            focus_nodes=None,
            main_db=None,
            draw_edgeless=False,
        )
        mock_parse_args.return_value = mock_args

        # Capture stdout to prevent output during tests
        original_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            dataflow_command.main()
        finally:
            sys.stdout = original_stdout

        # Verify draw_complete_data_flow was called with auto_open=True (default)
        mock_draw.assert_called_once()
        kwargs = mock_draw.call_args.kwargs
        self.assertEqual(
            kwargs.get("auto_open"), True
        )  # Use assertEqual instead of assertTrue

    @patch("sys.argv")
    @patch("src.dataflow_command.draw_complete_data_flow")
    @patch("argparse.ArgumentParser.parse_args")
    def test_command_interface_complete_no_auto_open(
        self, mock_parse_args, mock_draw, mock_argv
    ):
        """Test no-auto-open flag for complete flow diagram"""
        # Mock the argument parser to return auto_open=False
        import argparse

        mock_args = argparse.Namespace(
            metadata=self.test_file,
            type="complete",
            output=self.temp_dir,
            auto_open=False,  # Set auto_open to False
            focus_nodes=None,
            main_db=None,
            draw_edgeless=False,
        )
        mock_parse_args.return_value = mock_args

        # Capture stdout to prevent output during tests
        original_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            dataflow_command.main()
        finally:
            sys.stdout = original_stdout

        # Verify draw_complete_data_flow was called with auto_open=False
        mock_draw.assert_called_once()
        kwargs = mock_draw.call_args.kwargs
        self.assertEqual(
            kwargs.get("auto_open"), False
        )  # Use assertEqual instead of assertFalse

    @patch("sys.argv")
    @patch("src.dataflow_command.draw_focused_data_flow")
    @patch("argparse.ArgumentParser.parse_args")
    def test_command_interface_focused_auto_open(
        self, mock_parse_args, mock_draw, mock_argv
    ):
        """Test auto_open parameter for focused flow diagram"""
        # Mock the argument parser to return auto_open=True
        import argparse

        mock_args = argparse.Namespace(
            metadata=self.test_file,
            type="focused",
            output=self.temp_dir,
            auto_open=True,  # Set auto_open to True (default)
            focus_nodes=["test_view"],
            main_db=None,
            draw_edgeless=False,
            see_ancestors=True,  # Add the missing attributes
            see_descendants=True,
        )
        mock_parse_args.return_value = mock_args

        # Capture stdout to prevent output during tests
        original_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            dataflow_command.main()
        finally:
            sys.stdout = original_stdout

        # Verify draw_focused_data_flow was called with auto_open=True (default)
        mock_draw.assert_called_once()
        kwargs = mock_draw.call_args.kwargs
        self.assertEqual(
            kwargs.get("auto_open"), True
        )  # Use assertEqual instead of assertTrue

    @patch("sys.argv")
    @patch("src.dataflow_command.draw_focused_data_flow")
    @patch("argparse.ArgumentParser.parse_args")
    def test_command_interface_focused_no_auto_open(
        self, mock_parse_args, mock_draw, mock_argv
    ):
        """Test no-auto-open flag for focused flow diagram"""
        # Mock the argument parser to return auto_open=False
        import argparse

        mock_args = argparse.Namespace(
            metadata=self.test_file,
            type="focused",
            output=self.temp_dir,
            auto_open=False,  # Set auto_open to False
            focus_nodes=["test_view"],
            main_db=None,
            draw_edgeless=False,
            see_ancestors=True,  # Add the missing attributes
            see_descendants=True,
        )
        mock_parse_args.return_value = mock_args

        # Capture stdout to prevent output during tests
        original_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            dataflow_command.main()
        finally:
            sys.stdout = original_stdout

        # Verify draw_focused_data_flow was called with auto_open=False
        mock_draw.assert_called_once()
        kwargs = mock_draw.call_args.kwargs
        self.assertEqual(
            kwargs.get("auto_open"), False
        )  # Use assertEqual instead of assertFalse

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)


if __name__ == "__main__":
    unittest.main()
