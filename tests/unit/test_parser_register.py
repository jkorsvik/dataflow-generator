import unittest
import tempfile
import os
from src.parser_register import guess_database_type, _guess_by_parsing, DatabaseType

class TestParserRegister(unittest.TestCase):
    def test_guess_database_type_by_extension(self):
        # Should be None for ambiguous .sql extension per EXTENSION_MAP
        with tempfile.NamedTemporaryFile(suffix=".sql", mode="w", delete=False) as f:
            f.write("-- test SQL file")
            fname = f.name
        try:
            dbt = guess_database_type(fname)
            self.assertIsNone(dbt)
        finally:
            os.remove(fname)

    def test_guess_database_type_unknown(self):
        # Unknown extension and content
        with tempfile.NamedTemporaryFile(suffix=".unknown", mode="w", delete=False) as f:
            f.write("nonsense content")
            fname = f.name
        try:
            dbt = guess_database_type(fname)
            self.assertIsNone(dbt)
        finally:
            os.remove(fname)

    def test_guess_by_parsing_returns_none_for_ambiguous(self):
        # Should return None for ambiguous SQL
        ambiguous_sql = "SELECT * FROM foo"
        self.assertIsNone(_guess_by_parsing(ambiguous_sql))

if __name__ == "__main__":
    unittest.main()