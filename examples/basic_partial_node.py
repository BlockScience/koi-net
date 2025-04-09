import time
import logging
from rich.logging import RichHandler
from koi_net import NodeInterface
from koi_net.processor.handler import HandlerType
from koi_net.processor.knowledge_object import KnowledgeSource, KnowledgeObject
from koi_net.processor.interface import ProcessorInterface
from koi_net.protocol.event import EventType
from koi_net.protocol.edge import EdgeType
from koi_net.protocol.node import NodeProfile, NodeType
from koi_net.protocol.helpers import generate_edge_bundle
from rid_lib.types import KoiNetNode

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[RichHandler()]
)

logging.getLogger("koi_net").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)


node = NodeInterface(
    name="partial",
    profile=NodeProfile(
        node_type=NodeType.PARTIAL
    ),
    cache_directory_path="partial_node_rid_cache",
    event_queues_file_path="parital_node_event_queus.json",
    identity_file_path="partial_node_identity.json",
    first_contact="http://127.0.0.1:8000/koi-net"
)

@node.processor.register_handler(HandlerType.Network, rid_types=[KoiNetNode])
def coordinator_contact(processor: ProcessorInterface, kobj: KnowledgeObject):
    # when I found out about a new node
    if kobj.normalized_event_type != EventType.NEW: 
        return
    
    node_profile = kobj.bundle.validate_contents(NodeProfile)
    
    # looking for event provider of nodes
    if KoiNetNode not in node_profile.provides.event:
        return
    
    logger.info("Identified a coordinator!")
    logger.info("Proposing new edge")
    
    # queued for processing
    processor.handle(bundle=generate_edge_bundle(
        source=kobj.rid,
        target=node.identity.rid,
        edge_type=EdgeType.POLL,
        rid_types=[KoiNetNode]
    ))
    
    logger.info("Catching up on network state")
    
    payload = processor.network.request_handler.fetch_rids(kobj.rid, rid_types=[KoiNetNode])
    for rid in payload.rids:
        if rid == processor.identity.rid:
            logger.info("Skipping myself")
            continue
        if processor.cache.exists(rid):
            logger.info(f"Skipping known RID '{rid}'")
            continue
        
        # marked as external since we are handling RIDs from another node
        # will fetch remotely instead of checking local cache
        processor.handle(rid=rid, source=KnowledgeSource.External)
    logger.info("Done")
    


node.start()

while True:
    for event in node.network.poll_neighbors():
        node.processor.handle(event=event, source=KnowledgeSource.External)
    node.processor.flush_kobj_queue()
    
    time.sleep(5)