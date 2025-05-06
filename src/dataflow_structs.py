from typing import TypedDict, Optional

class InvalidSQLError(Exception):
    pass

class NodeInfo(TypedDict):
    type: str
    database: str
    full_name: str
    definition: Optional[str]
