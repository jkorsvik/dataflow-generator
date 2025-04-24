import os
import sys
import tempfile
import shutil
import pytest
from src import dataflow_command

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
        "prog", "--metadata", vql_path, "--type", "focused", "--focus-nodes", "v_test", "--output", out_dir
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
    sys_argv = [
        "prog", "--metadata", vql_path, "--main-db", "db1", "--output", out_dir
    ]
    monkeypatch.setattr(sys, "argv", sys_argv)
    dataflow_command.main()
    files = os.listdir(out_dir)
    assert any(f.endswith(".html") for f in files)
    shutil.rmtree(out_dir)
    os.remove(vql_path)
