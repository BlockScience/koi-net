from rid_lib.core import RIDType
from rid_lib.ext.bundle import Bundle
from rid_lib.types import KoiNetEdge
from rid_lib.types.koi_net_node import KoiNetNode
from .edge import EdgeProfile, EdgeStatus, EdgeType

def generate_edge_bundle(
    source: KoiNetNode,
    target: KoiNetNode,
    rid_types: list[RIDType],
    edge_type: EdgeType
) -> Bundle:
    edge_rid = KoiNetEdge.generate(source, target)
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