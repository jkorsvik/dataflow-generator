from enum import Enum, auto
import os
import re
from typing import Optional, Union
from sqlfluff.core import Linter

from .parsers import (
    parser_denodo,
    parser_mysql,
    parser_postgres,
    parser_sqlserver,
    parser_oracle,
    parser_sqlite,
    parser_snowflake,
)


class DatabaseType(Enum):
    DENODO = auto()
    SNOWFLAKE = auto()
    POSTGRESQL = auto()
    ANSI = auto()  # FOCUS ON THE ONES ABOVE FIRST
    MYSQL = auto()
    SQLITE = auto()
    SQLSERVER = auto()
    ORACLE = auto()
    # …add more as needed


# Each entry should point to a module with a `parse_dump(file_path)` function.
_PARSER_REGISTRY = {
    DatabaseType.MYSQL: parser_mysql,
    DatabaseType.POSTGRESQL: parser_postgres,
    DatabaseType.ANSI: parser_postgres,
    DatabaseType.SNOWFLAKE: parser_snowflake,
    DatabaseType.SQLSERVER: parser_sqlserver,
    DatabaseType.ORACLE: parser_oracle,
    DatabaseType.DENODO: parser_denodo,
    DatabaseType.SQLITE: parser_sqlite,
}


EXTENSION_MAP = {
    ".sql": None,  # ambiguous
    ".psql": DatabaseType.POSTGRESQL,
    ".pgdump": DatabaseType.POSTGRESQL,
    ".vql": DatabaseType.DENODO,
    ".ora": DatabaseType.ORACLE,
    ".bcp": DatabaseType.SQLSERVER,
    # …etc.
}

HEADER_KEYWORDS = {
    DatabaseType.MYSQL: re.compile(r"-- MySQL dump", re.IGNORECASE),
    DatabaseType.POSTGRESQL: re.compile(r"-- PostgreSQL database dump", re.IGNORECASE),
    DatabaseType.SQLSERVER: re.compile(r"-- Microsoft SQL Server", re.IGNORECASE),
    DatabaseType.ORACLE: re.compile(r"/\* Oracle SQL dump \*/", re.IGNORECASE),
    DatabaseType.DENODO: re.compile(r"<VQL>", re.IGNORECASE),
}

KEYWORD_COUNTS = {
    DatabaseType.MYSQL: [r"ENGINE\s*=", r"AUTO_INCREMENT"],
    DatabaseType.POSTGRESQL: [r"SERIAL", r"OWNER TO", r"SET search_path"],
    DatabaseType.SQLSERVER: [r"\bGO\b", r"IDENTITY\s*\(", r"MERGE\s+INTO"],
    DatabaseType.ORACLE: [r"\bSEQUENCE\b", r"SPOOL\s+", r"VARCHAR2"],
    # Denodo you've already captured via .vql extension or header
}


def _guess_by_parsing(sql_text: str) -> Optional[DatabaseType]:
    # Try each dialect and count parse errors
    errors_per_dialect = {}
    for dbt in [
        DatabaseType.MYSQL,
        DatabaseType.POSTGRESQL,
        DatabaseType.SQLSERVER,
        DatabaseType.ORACLE,
    ]:
        dialect = {
            DatabaseType.MYSQL: "mysql",
            DatabaseType.POSTGRESQL: "postgres",
            DatabaseType.SQLSERVER: "tsql",
            DatabaseType.ORACLE: "oracle",
        }[dbt]
        linter = Linter(dialect=dialect)
        result = linter.lint_string(sql_text)
        errors_per_dialect[dbt] = len(result.get_violations())

    best_dbt, best_errs = min(errors_per_dialect.items(), key=lambda kv: kv[1])
    # Only pick if clearly better
    if best_errs < min(e for dbt, e in errors_per_dialect.items() if dbt != best_dbt):
        return best_dbt
    return None


def guess_database_type(file_path: Union[str, os.PathLike]) -> Optional[DatabaseType]:
    # 1) By extension
    ext = os.path.splitext(file_path)[1].lower()
    if ext in EXTENSION_MAP and EXTENSION_MAP[ext] is not None:
        return EXTENSION_MAP[ext]

    # 2) Read the first chunk
    head = ""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        head = f.read(32_768)  # first 32 KB

    # 3) Header‐comment sniff
    for dbt, pattern in HEADER_KEYWORDS.items():
        if pattern.search(head):
            return dbt

    # 4) Keyword‐frequency scoring
    scores = {dbt: 0 for dbt in KEYWORD_COUNTS}
    for dbt, regex_list in KEYWORD_COUNTS.items():
        for regex in regex_list:
            matches = re.findall(regex, head, flags=re.IGNORECASE)
            scores[dbt] += len(matches)
    best, best_score = max(scores.items(), key=lambda kv: kv[1])
    if best_score >= 2:  # threshold: at least 2 hits
        return best

    # 5) Fallback to SQL‐dialect parser ranking
    return _guess_by_parsing(head)
