from typing import TypedDict, Optional

class InvalidSQLError(Exception):
    pass

SQL_PATTERNS = [
    r"\b(CREATE|SELECT|FROM|JOIN|VIEW|TABLE)\b",
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER)\b",
]

class NodeInfo(TypedDict):
    type: str
    database: str
    full_name: str
    definition: Optional[str]
