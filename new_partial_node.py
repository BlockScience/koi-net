import logging
from rich.logging import RichHandler
from rid_lib.ext import Cache, Bundle, Event, EventType
from koi_net import NodeInterface
from koi_net.models import NodeModel, NodeType, Provides, EdgeModel
from koi_net.rid_types import KoiNetEdge, KoiNetNode
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[RichHandler()]
)

logging.getLogger("koi_net").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

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

breakpoint()

@node.processor.register_event_handler([KoiNetEdge])
def edge_negotiation_handler(event: Event, event_type: EventType):
    bundle = event.bundle or node.cache.read(event.rid)
    edge_profile = EdgeModel.model_validate(bundle.contents)

    logger.info("Handling edge negotiation")

    # indicates peer subscriber
    if edge_profile.source == node.network.me:                
        if edge_profile.status != "proposed":
            # TODO: handle other status
            return
        
        if any(context not in my_profile.provides.event for context in edge_profile.rid_types):
            # indicates node subscribing to unsupported event
            # TODO: either reject or repropose agreement
            logger.info("Requested contexts not provided by this node")
            event = Event.from_rid(EventType.FORGET, event.rid)

            
        elif not node.cache.read(edge_profile.target):
            # TODO: handle unknown subscriber node (delete edge?)
            logger.warning("Peer unknown to this node")
            event = Event.from_bundle(EventType.FORGET, event.rid)

        else:
            # approve edge profile
            edge_profile.status = "approved"
            updated_bundle = Bundle.generate(bundle.manifest.rid, edge_profile.model_dump())
            
            event = Event.from_bundle(EventType.UPDATE, updated_bundle)
            
        node.network.push_event_to(event, edge_profile.target, flush=True)
        node.processor.handle_event(event)
        
    elif edge_profile.target == node.network.me:
        logger.info("Edge approved by other node!")


# if you don't know anybody
if len(node.network.graph.dg.nodes) == 1:
    logger.info("I don't know any other nodes, shaking hands with coordinator")
    resp = node.network.adapter.broadcast_events(
        url=COORDINATOR_URL,
        events=[Event.from_bundle(EventType.NEW, my_bundle)]
    )


while True:
    resp = node.network.adapter.poll_events(url=COORDINATOR_URL, rid=my_rid)
    logger.info(f"Received {len(resp.events)} event(s)")
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
    
    
    if len(node.network.graph.get_neighbors(direction="in")) == 0:
        logger.info("I don't have any neighbors, subscribing to peer")
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
    
    time.sleep(0.5)
