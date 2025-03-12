from rid_lib.ext import Cache, Bundle, Event, EventType
from koi_net import EdgeModel, NodeModel, NodeType
from rid_types import KoiNetEdge, KoiNetNode
from coordinator.network import NetworkInterface
from coordinator.event_handler import KnowledgeProcessor

COORDINATOR_URL = "http://127.0.0.1:8000/koi-net"

cache = Cache("partial_node_cache")

my_rid = KoiNetNode("new_partial_node")
my_profile = NodeModel(
    node_type=NodeType.PARTIAL,
    provides={}
)
my_bundle = Bundle.generate(my_rid, my_profile.model_dump())

network = NetworkInterface("none.json", cache, me=my_rid)
processor = KnowledgeProcessor(cache, network)

processor.handle_state(my_bundle)

print(network.state.get_sub_rids())

# if you don't know anybody
if len(network.state.dg.nodes) == 1:
    resp = network.adapter.broadcast_events(
        url=COORDINATOR_URL,
        events=[
            Event.from_bundle(EventType.NEW, my_bundle)
        ]
    )
    print(resp)

    resp = network.adapter.poll_events(url=COORDINATOR_URL, rid=my_rid)
    print(resp)
    processor.handle_event(resp.events[0])

    
    coordinator_rid = resp.events[0].rid
    
    bundle = Bundle.generate(
        KoiNetEdge("testing_edge"),
        EdgeModel(
            source=coordinator_rid,
            target=my_rid,
            comm_type="poll",
            contexts=[
                KoiNetNode.context,
                KoiNetEdge.context
            ],
            status="proposed"
        ).model_dump()
    )
    
    network.adapter.broadcast_events(
        node=coordinator_rid,
        events=[
            Event.from_bundle(EventType.NEW, bundle)
        ]
    )
    
    resp = network.adapter.poll_events(url=COORDINATOR_URL, rid=my_rid)
    processor.handle_event(resp.events[0])

