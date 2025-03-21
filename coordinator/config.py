from koi_net.models import NodeModel, NodeType, Provides
from koi_net.rid_types import KoiNetNode, KoiNetEdge

host = "127.0.0.1"
port = 8000

this_node_rid = KoiNetNode("coordinator")
this_node_profile = NodeModel(
    base_url=f"http://{host}:{port}/koi-net",
    node_type=NodeType.FULL,
    provides=Provides(
        event=[KoiNetNode, KoiNetEdge],
        state=[KoiNetNode, KoiNetEdge]
    )
)

api_prefix = "/koi-net"