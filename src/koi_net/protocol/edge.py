from enum import StrEnum
from pydantic import BaseModel
from rid_lib import RIDType
from rid_lib.types import KoiNetNode


class EdgeStatus(StrEnum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    
class EdgeType(StrEnum):
    WEBHOOK = "WEBHOOK"
    POLL = "POLL"

class EdgeProfile(BaseModel):
    source: KoiNetNode
    target: KoiNetNode
    edge_type: EdgeType
    status: EdgeStatus
    rid_types: list[RIDType]
