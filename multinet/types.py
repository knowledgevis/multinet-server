"""Custom types for Multinet codebase."""
from typing import Dict, Set
from typing_extensions import Literal, TypedDict

EdgeDirection = Literal["all", "incoming", "outgoing"]
TableType = Literal["all", "node", "edge"]


class EdgeTableProperties(TypedDict):
    """Describes gathered information about an edge table."""

    # Dictionary mapping all referenced tables to the referenced keys within that table
    table_keys: Dict[str, Set[str]]

    # Keeps track of which tables are referenced in the _from column
    from_tables: Set[str]

    # Keeps track of which tables are referenced in the _to column
    to_tables: Set[str]
