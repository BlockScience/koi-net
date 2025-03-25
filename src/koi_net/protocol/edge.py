from pydantic import BaseModel
from rid_lib import RIDType
from rid_lib.types import KoiNetNode


class EdgeModel(BaseModel):
    source: KoiNetNode
    target: KoiNetNode
    comm_type: str
    rid_types: list[RIDType]
    status: str