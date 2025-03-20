from koi_net.models import NodeModel, NodeType, Provides
from koi_net.rid_types import KoiNetNode, KoiNetEdge

this_node_rid = KoiNetNode("coordinator")
this_node_profile = NodeModel(
    base_url="http://127.0.0.1:8000/koi-net",
    node_type=NodeType.FULL,
    provides=Provides(
        event=[KoiNetNode, KoiNetEdge],
        state=[KoiNetNode, KoiNetEdge]
    )
)

api_prefix = "/koi-net"