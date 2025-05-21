import unittest
from src.dataflow import (
    normalize_file_path,
    normalize_path_for_platform,
    is_sql_file,
)

class TestDataflowHelpers(unittest.TestCase):
    def test_normalize_file_path(self):
        import os
        self.assertEqual(
            normalize_file_path("foo//bar/../baz.sql"),
            os.path.abspath("foo/baz.sql"),
        )
        self.assertEqual(
            normalize_file_path("./foo/./bar.sql"),
            os.path.abspath("foo/bar.sql"),
        )
        self.assertEqual(
            normalize_file_path("foo/bar.sql"),
            os.path.abspath("foo/bar.sql"),
        )

    def test_normalize_path_for_platform(self):
        import os
        import sys
        if sys.platform.startswith("win"):
            self.assertEqual(
                normalize_path_for_platform("foo/bar\\baz.sql"),
                os.path.abspath("foo\\bar\\baz.sql"),
            )
        else:
            # On Unix, the function does not convert backslashes, so expect the mixed path
            self.assertEqual(
                normalize_path_for_platform("foo\\bar/baz.sql"),
                os.path.abspath("foo\\bar/baz.sql"),
            )

    def test_is_sql_file(self):
        valid = [
            "test.sql", "test.vql", "test.ddl", "test.dml", "test.hql",
            "test.pls", "test.plsql", "test.proc", "test.psql", "test.tsql", "test.view"
        ]
        invalid = ["test.txt", "test.py", "test", "test.sql.txt"]
        for f in valid:
            self.assertTrue(is_sql_file(f), f"{f} should be recognized as SQL file")
        for f in invalid:
            self.assertFalse(is_sql_file(f), f"{f} should not be recognized as SQL file")

if __name__ == "__main__":
    unittest.main()