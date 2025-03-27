import time
import logging
from rich.logging import RichHandler
from rid_lib.ext import Cache, Bundle
from rid_lib.types.slack_channel import SlackChannel
from koi_net import NodeInterface, network
from koi_net.protocol import (
    Event, 
    EventType, 
    EdgeModel, 
    NodeModel, 
    NodeType, 
    NodeProvides
)
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
    rid=KoiNetNode("new_partial_node", "uuid"),
    profile=NodeModel(
        node_type=NodeType.PARTIAL,
        provides=NodeProvides()
    ),
    cache=Cache("_cache-partial-node"),
)

# if you don't know anybody
if len(node.network.graph.dg.nodes) == 1:
    logger.info("I don't know any other nodes, shaking hands with coordinator")
    resp = node.network.adapter.broadcast_events(
        url=COORDINATOR_URL,
        events=[Event.from_bundle(EventType.NEW, node.identity.bundle)]
    )
    
attempted_subscription = False

while True:
    resp = node.network.adapter.poll_events(url=COORDINATOR_URL, rid=node.identity.rid)
    logger.info(f"Received {len(resp.events)} event(s)")
    for event in resp.events:
        node.processor.handle_event(event)
    
    if len(resp.events) == 0:
        break
    
    has_edges = False
    for rid in node.cache.list_rids(rid_types=[KoiNetNode, KoiNetEdge]):
        if type(rid) == KoiNetEdge:
            has_edges = True
        elif type(rid) == KoiNetNode:
            if rid != node.identity.rid:
                peer = rid
    
    
    if len(node.network.graph.get_neighbors(direction="in")) == 0 and not attempted_subscription:
        logger.info("I don't have any neighbors, subscribing to peer")
        bundle = Bundle.generate(
            KoiNetEdge("coordinator->partial_edge"),
            EdgeModel(
                source=peer,
                target=node.identity.rid,
                comm_type="poll",
                rid_types=[
                    SlackChannel
                ],
                status="proposed"
            ).model_dump()
        )
        
        node.processor.handle_bundle(bundle)
        
        node.network.push_event_to(
            node=peer,
            event=Event.from_bundle(EventType.NEW, bundle),
            flush=True)
        
        attempted_subscription = True
        
    time.sleep(1)