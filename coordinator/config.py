from koi_net import Node, NodeType
from rid_types import KoiNetNode, KoiNetEdge

this_node_rid = KoiNetNode("coordinator")
this_node_profile = Node(
    base_url="http://127.0.0.1:8000",
    node_type=NodeType.FULL,
    provides={
        "event": [KoiNetNode.context, KoiNetEdge.context],
        "state": [KoiNetNode.context, KoiNetEdge.context]
    }
)
