from rid_lib.ext import Cache, Bundle, Event, EventType
from koi_net import EdgeModel, NodeModel, NodeType
from rid_types import KoiNetEdge, KoiNetNode
from coordinator.network import NetworkInterface
from coordinator.event_handler import KnowledgeProcessor
import time

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
    

while True:
    resp = network.adapter.poll_events(url=COORDINATOR_URL, rid=my_rid)
    if resp.events: print("handling", len(resp.events), "events")
    for event in resp.events:
        processor.route_event(event)
    
    
    has_edges = False
    for rid in cache.read_all_rids():
        if rid.context == KoiNetEdge.context:
            has_edges = True
        elif rid.context == KoiNetNode.context:
            if rid != network.me:
                peer = rid
    
    
    if len(network.state.get_sub_rids(network.me)) == 10:
        print("subscribing to coordinator")
        bundle = Bundle.generate(
            KoiNetEdge("coordinator->partial_edge"),
            EdgeModel(
                source=peer,
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
            node=peer,
            events=[
                Event.from_bundle(EventType.NEW, bundle)
            ]
        )
    
    time.sleep(5)
