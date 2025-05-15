import unittest
import tempfile
import os
import shutil
from unittest.mock import patch
from src.path_utils import ensure_data_dirs_exist, read_settings, write_settings

class TestPathUtils(unittest.TestCase):
    def test_ensure_data_dirs_exist(self):
        # Patch before importing the module to ensure correct directory is used
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.path_utils.platformdirs.user_data_dir", return_value=tmpdir):
                import importlib
                import sys
                if "src.path_utils" in sys.modules:
                    importlib.reload(sys.modules["src.path_utils"])
                from src.path_utils import ensure_data_dirs_exist
                import pathlib
                ensure_data_dirs_exist()
                expected = pathlib.Path(tmpdir) / "data-flow-data"
                self.assertTrue(expected.exists())

    def test_read_write_settings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = os.path.join(tmpdir, "settings.json")
            with patch("src.path_utils.platformdirs.user_data_dir", return_value=tmpdir):
                # Write settings
                data = {"foo": "bar"}
                write_settings(data)
                # Read settings
                result = read_settings()
                self.assertEqual(result, data)

    def test_read_settings_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.path_utils.platformdirs.user_data_dir", return_value=tmpdir):
                import pathlib
                # Remove settings file if it exists
                settings_file = pathlib.Path(tmpdir) / "data-flow-data" / "settings.json"
                if settings_file.exists():
                    settings_file.unlink()
                from src.path_utils import read_settings
                result = read_settings()
                self.assertEqual(result, {})

if __name__ == "__main__":
    unittest.main()