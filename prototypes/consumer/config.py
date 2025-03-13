from koi_net import NodeModel, NodeType
from koi_net.rid_types import KoiNetNode, KoiNetEdge

this_node_rid = KoiNetNode("consumer")
this_node_profile = NodeModel(
    base_url="http://127.0.0.1:8001/koi-net",
    node_type=NodeType.FULL,
    provides={
        "event": [],
        "state": []
    }
)
