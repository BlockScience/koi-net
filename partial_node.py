from koi_net import Edge, EventArray, KoiNetPath, Node, NodeType
from rid_types import KoiNetEdge, KoiNetNode
import httpx
from rid_lib.ext import Bundle, Event, EventType


COORDINATOR_URL = "http://127.0.0.1:8000/koi-net"

my_rid = KoiNetNode("partial_node")
my_profile = Node(
    node_type=NodeType.PARTIAL,
    provides={}
)
my_bundle = Bundle.generate(my_rid, my_profile.model_dump())

resp = httpx.post(
    COORDINATOR_URL + KoiNetPath.HANDSHAKE,
    data=my_bundle.model_dump_json()
)

peer_bundle = Bundle(**resp.json())
peer_profile = Node(**peer_bundle.contents)
print(peer_bundle.manifest.rid)

proposed_edge = Edge(
    source=peer_bundle.manifest.rid,
    target=my_rid,
    comm_type="poll",
    contexts=[
        "orn:koi-net.node",
        "orn:koi-net.edge"
    ],
    status="proposed"
)
edge_bundle = Bundle.generate(
    KoiNetEdge("test_edge"),
    proposed_edge.model_dump()
)

event = Event(
    rid=edge_bundle.manifest.rid,
    event_type=EventType.NEW,
    bundle=edge_bundle
)

resp = httpx.post(
    COORDINATOR_URL + KoiNetPath.EVENTS_BROADCAST,
    data=EventArray([event]).model_dump_json()
)

resp = httpx.get(
    COORDINATOR_URL + KoiNetPath.EVENTS_POLL + "?rid=" + str(my_rid)
)

events = EventArray(resp.json()).root

for e in events:
    print(e.event_type, e.rid)

# print(events)