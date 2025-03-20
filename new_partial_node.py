from rid_lib.ext import Cache, Bundle, Event, EventType
from koi_net import NodeInterface
from koi_net.models import NodeModel, NodeType, Provides, EdgeModel
from koi_net.rid_types import KoiNetEdge, KoiNetNode
import time

COORDINATOR_URL = "http://127.0.0.1:8000/koi-net"
my_rid = KoiNetNode("new_partial_node")

node = NodeInterface(
    rid=my_rid,
    cache=Cache("_cache-partial-node")
)

my_profile = NodeModel(
    node_type=NodeType.PARTIAL,
    provides=Provides(
        state=[KoiNetNode, KoiNetEdge], 
        event=[KoiNetNode, KoiNetEdge]
    )
)

node.processor.handle_state(
    Bundle.generate(my_rid, my_profile.model_dump()))

my_bundle = node.cache.read(my_rid)




print(node.network.graph.get_neighbors(direction="out", status="approved"))


@node.processor.register_event_handler([KoiNetEdge])
def edge_negotiation_handler(event: Event, event_type: EventType):
    print("trigger negotiation handler")
    bundle = event.bundle or node.cache.read(event.rid)
    edge_profile = EdgeModel(**bundle.contents)
    

    # indicates peer subscriber
    if edge_profile.source == node.network.me:
        edge_profile = EdgeModel(**bundle.contents)
        
        print("proposed edge", edge_profile)
        
        if edge_profile.status != "proposed":
            # TODO: handle other status
            return
        
        if any(context not in my_profile.provides.event for context in edge_profile.rid_types):
            # indicates node subscribing to unsupported event
            # TODO: either reject or repropose agreement
            print("requested context not provided")
            return
            
        if not node.cache.read(edge_profile.target):
            # TODO: handle unknown subscriber node (delete edge?)
            print("unknown subscriber")
            return
        
        # approve edge profile
        edge_profile.status = "approved"
        updated_bundle = Bundle.generate(bundle.manifest.rid, edge_profile.model_dump())
        
        event = Event.from_bundle(EventType.UPDATE, updated_bundle)
        
        node.network.push_event_to(event, edge_profile.target, flush=True)
        # self.network.flush_webhook_queue(edge_profile.target)
        node.processor.handle_event(event)
        
    elif edge_profile.target == node.network.me:
        print("other node approved my edge!")


# if you don't know anybody
if len(node.network.graph.dg.nodes) == 1:
    print("i don't know anyone...")
    resp = node.network.adapter.broadcast_events(
        url=COORDINATOR_URL,
        events=[
            Event.from_bundle(EventType.NEW, my_bundle)
        ]
    )


while True:
    resp = node.network.adapter.poll_events(url=COORDINATOR_URL, rid=my_rid)
    if resp.events: print("handling", len(resp.events), "events")
    for event in resp.events:
        node.processor.handle_event(event)
    
    if len(resp.events) == 0:
        break
    
    has_edges = False
    for rid in node.cache.read_all_rids():
        if rid.context == KoiNetEdge.context:
            has_edges = True
        elif rid.context == KoiNetNode.context:
            if rid != node.network.me:
                peer = rid
    
    print("I know this many subscribers", node.network.graph.get_neighbors(direction="out"))
    
    if len(node.network.graph.get_neighbors(direction="in")) == 0:
        print("subscribing to coordinator")
        bundle = Bundle.generate(
            KoiNetEdge("coordinator->partial_edge"),
            EdgeModel(
                source=peer,
                target=my_rid,
                comm_type="poll",
                rid_types=[
                    KoiNetNode,
                    KoiNetEdge
                ],
                status="proposed"
            ).model_dump()
        )
        
        node.network.adapter.broadcast_events(
            node=peer,
            events=[
                Event.from_bundle(EventType.NEW, bundle)
            ]
        )
    
    time.sleep(1)
