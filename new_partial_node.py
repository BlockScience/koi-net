import time
import logging
from rich.logging import RichHandler
from rid_lib.ext import Cache, Bundle
from koi_net import NodeInterface
from koi_net.processor.handler import HandlerType, InternalEvent
from koi_net.processor.interface import ProcessorInterface
from koi_net.protocol.event import Event, EventType
from koi_net.protocol.edge import EdgeModel, EdgeType, EdgeStatus
from koi_net.protocol.node import NodeModel, NodeType, NodeProvides
from rid_lib.types import KoiNetEdge, KoiNetNode

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[RichHandler()]
)

logging.getLogger("koi_net").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

COORDINATOR_URL = "http://127.0.0.1:8000/koi-net"

node = NodeInterface(
    rid=KoiNetNode("partial_node", "uuid"),
    profile=NodeModel(
        node_type=NodeType.PARTIAL,
        provides=NodeProvides()
    ),
    cache=Cache("_cache-partial-node"),
)

@node.processor.register_handler(HandlerType.Cache, rid_types=[KoiNetNode])
def coordinator_contact(processor: ProcessorInterface, ievent: InternalEvent):
    if ievent.event_type != EventType.NEW: 
        return
    
    node_profile = ievent.bundle.validate_contents(NodeModel)
    if KoiNetNode not in node_profile.provides.event:
        return
    
    logger.info("Identified a coordinator!")
    logger.info("Proposing new edge")
    bundle = Bundle.generate(
        KoiNetEdge.generate(ievent.rid, processor.identity.rid),
        EdgeModel(
            source=ievent.rid,
            target=node.identity.rid,
            edge_type=EdgeType.POLL,
            rid_types=[KoiNetNode],
            status=EdgeStatus.PROPOSED
        ).model_dump()
    )
    
    node.processor.handle_bundle(bundle, queue=True)
    
    # node.network.push_event_to(
    #     node=ievent.rid,
    #     event=Event.from_bundle(EventType.NEW, bundle),
    #     flush=True)
    
    logger.info("Catching up on network state")
    
    payload = processor.network.adapter.fetch_rids(ievent.rid, rid_types=[KoiNetNode])
    for rid in payload.rids:
        if rid == processor.identity.rid:
            # already know who I am!
            continue
        processor.handle_rid(rid, queue=True)
    

# if you don't know anybody
if len(node.network.graph.dg.nodes) == 1:
    logger.info("I don't know any other nodes, shaking hands with coordinator")
    resp = node.network.adapter.broadcast_events(
        url=COORDINATOR_URL,
        events=[Event.from_bundle(EventType.NEW, node.identity.bundle)]
    )
    

while True:
    resp = node.network.adapter.poll_events(url=COORDINATOR_URL, rid=node.identity.rid)
    logger.info(f"Received {len(resp.events)} event(s)")
    for event in resp.events:
        node.processor.handle_event(event)
    
 
    time.sleep(3)