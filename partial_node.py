from coordinator.network_models import PollEvents
from koi_net import EdgeModel, EventArrayModel, KoiNetPath, NodeModel, NodeType
from rid_types import KoiNetEdge, KoiNetNode
import httpx
from rid_lib.ext import Bundle, Event, EventType


COORDINATOR_URL = "http://127.0.0.1:8000/koi-net"

attempt = "1"

my_rid = KoiNetNode("partial_node" + attempt)
my_profile = NodeModel(
    node_type=NodeType.PARTIAL,
    provides={}
)
my_bundle = Bundle.generate(my_rid, my_profile.model_dump())

# resp = httpx.post(
#     COORDINATOR_URL + KoiNetPath.HANDSHAKE,
#     data=my_bundle.model_dump_json()
# )

# input()

# peer_bundle = Bundle(**resp.json())
# peer_profile = NodeModel(**peer_bundle.contents)
# print(peer_bundle.manifest.rid)

# proposed_edge = EdgeModel(
#     source=peer_bundle.manifest.rid,
#     target=my_rid,
#     comm_type="poll",
#     contexts=[
#         "orn:koi-net.node",
#         "orn:koi-net.edge"
#     ],
#     status="proposed"
# )
# edge_bundle = Bundle.generate(
#     KoiNetEdge("test_edge" + attempt),
#     proposed_edge.model_dump()
# )

# event = Event(
#     rid=edge_bundle.manifest.rid,
#     event_type=EventType.NEW,
#     bundle=edge_bundle
# )

# resp = httpx.post(
#     COORDINATOR_URL + KoiNetPath.EVENTS_BROADCAST,
#     data=EventArrayModel([event]).model_dump_json()
# )

# input()

resp = httpx.post(
    COORDINATOR_URL + KoiNetPath.EVENTS_POLL,
    data=PollEvents(rid=str(my_rid)).model_dump_json()
)

data = resp.json()

events = EventArrayModel(data).root

for e in events:
    print(e.event_type, e.rid)

# print(events)