import logging
from rid_lib.types import KoiNetNode, KoiNetEdge
from rid_lib.ext import Bundle
from koi_net.processor import ProcessorInterface, InternalEvent, HandlerType
from koi_net.protocol.edge import EdgeModel
from koi_net.protocol.event import Event, EventType
from .core import node

logger = logging.getLogger(__name__)


@node.processor.register_handler(HandlerType.Network, rid_types=[KoiNetNode])
def handshake_handler(proc: ProcessorInterface, ievent: InternalEvent):    
    logger.info("Handling node handshake")

    # only respond if node is unknown to me
    if ievent.event_type != EventType.NEW:
        logger.info("Peer already know to this node, ignoring")
        return
        
    logger.info("Sharing this node's bundle with peer")
    proc.network.push_event_to(
        event=Event.from_bundle(EventType.NEW, proc.my.bundle),
        node=ievent.rid,
        flush=True
    )
    
    logger.info("Proposing new edge")
    edge_bundle = Bundle.generate(
        KoiNetEdge("partial->coordinator"),
        EdgeModel(
            source=ievent.rid,
            target=proc.my.rid,
            comm_type="webhook",
            rid_types=[KoiNetNode, KoiNetEdge],
            status="proposed"
        ).model_dump()
    )
        
    proc.network.push_event_to(
        event=Event.from_manifest(EventType.NEW, edge_bundle.manifest),
        node=ievent.rid,
        flush=True
    )
    
    proc.handle_bundle(edge_bundle)
