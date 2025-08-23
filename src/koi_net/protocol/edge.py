from enum import StrEnum
from pydantic import BaseModel
from rid_lib import RIDType
from rid_lib.ext.bundle import Bundle
from rid_lib.ext.utils import sha256_hash
from rid_lib.types import KoiNetEdge, KoiNetNode


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


def generate_edge_bundle(
    source: KoiNetNode,
    target: KoiNetNode,
    rid_types: list[RIDType],
    edge_type: EdgeType
) -> Bundle:
    edge_rid = KoiNetEdge(sha256_hash(
        str(source) + str(target)
    ))
    edge_profile = EdgeProfile(
        source=source,
        target=target,
        rid_types=rid_types,
        edge_type=edge_type,
        status=EdgeStatus.PROPOSED
    )
    edge_bundle = Bundle.generate(
        edge_rid,
        edge_profile.model_dump()
    )
    return edge_bundle