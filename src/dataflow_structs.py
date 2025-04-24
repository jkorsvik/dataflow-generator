from enum import Enum
from typing import TypedDict


class InvalidSQLError(Exception):
    pass


class NodeInfo(TypedDict):
    type: str
    database: str
    full_name: str
