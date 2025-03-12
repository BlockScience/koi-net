from rid_lib.ext import Cache, Bundle, Event, EventType
from koi_net import EdgeModel, NodeModel, NodeType, Provides
from rid_types import KoiNetEdge, KoiNetNode
from coordinator.network import NetworkInterface
from coordinator.processor import HandlerType, KnowledgeProcessor
import time

COORDINATOR_URL = "http://127.0.0.1:8000/koi-net"

cache = Cache("partial_node_cache")

my_rid = KoiNetNode("new_partial_node")
my_profile = NodeModel(
    node_type=NodeType.PARTIAL,
    provides=Provides(state=[KoiNetNode.context, KoiNetEdge.context], event=[KoiNetNode.context, KoiNetEdge.context])
)
my_bundle = Bundle.generate(my_rid, my_profile.model_dump())

network = NetworkInterface("none.json", cache, me=my_rid)
processor = KnowledgeProcessor(cache, network)


@processor.register_handler(
    contexts=[KoiNetEdge.context],
    handler_type=HandlerType.EVENT
)
def edge_negotiation_handler(event: Event, event_type: EventType):
    print("trigger negotiation handler")
    bundle = event.bundle or cache.read(event.rid)
    edge_profile = EdgeModel(**bundle.contents)
    

    # indicates peer subscriber
    if edge_profile.source == network.me:
        edge_profile = EdgeModel(**bundle.contents)
        
        print("proposed edge", edge_profile)
        
        if edge_profile.status != "proposed":
            # TODO: handle other status
            return
        
        if any(context not in network.state.get_node(network.me).provides.event for context in edge_profile.contexts):
            # indicates node subscribing to unsupported event
            # TODO: either reject or repropose agreement
            print("requested context not provided")
            return
            
        if not cache.read(edge_profile.target):
            # TODO: handle unknown subscriber node (delete edge?)
            print("unknown subscriber")
            return
        
        # approve edge profile
        edge_profile.status = "approved"
        updated_bundle = Bundle.generate(bundle.manifest.rid, edge_profile.model_dump())
        
        event = Event.from_bundle(EventType.UPDATE, updated_bundle)
        
        network.push_event_to(event, edge_profile.target, flush=True)
        # self.network.flush_webhook_queue(edge_profile.target)
        processor.handle_event(event)
        
    elif edge_profile.target == network.me:
        print("other node approved my edge!")


processor.handle_state(my_bundle)


# if you don't know anybody
if len(network.state.dg.nodes) == 1:
    resp = network.adapter.broadcast_events(
        url=COORDINATOR_URL,
        events=[
            Event.from_bundle(EventType.NEW, my_bundle)
        ]
    )
    print(resp)    

print("publishers", network.state.get_pub_rids())
print("subscribers", network.state.get_sub_rids())

while True:
    resp = network.adapter.poll_events(url=COORDINATOR_URL, rid=my_rid)
    if resp.events: print("handling", len(resp.events), "events")
    for event in resp.events:
        processor.handle_event(event)
    
    if len(resp.events) == 0:
        break
    
    has_edges = False
    for rid in cache.read_all_rids():
        if rid.context == KoiNetEdge.context:
            has_edges = True
        elif rid.context == KoiNetNode.context:
            if rid != network.me:
                peer = rid
    
    
    if len(network.state.get_sub_rids()) == 0:
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
