from enum import StrEnum
from pydantic import BaseModel, Field
from rid_lib import RIDType


class NodeType(StrEnum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"

class NodeProvides(BaseModel):
    event: list[RIDType] = Field(default_factory=list)
    state: list[RIDType] = Field(default_factory=list)

class NodeProfile(BaseModel):
    base_url: str | None = None
    node_type: NodeType
    provides: NodeProvides = NodeProvides()
    public_key: str | None = None