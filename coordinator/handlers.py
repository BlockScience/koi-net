import logging
from rid_lib.types import KoiNetNode, KoiNetEdge
from rid_lib.ext import Bundle
from koi_net.processor import ProcessorInterface
from koi_net.processor.handler import HandlerType
from koi_net.processor.knowledge_object import KnowledgeObject
from koi_net.protocol.edge import EdgeModel, EdgeStatus, EdgeType
from koi_net.protocol.event import Event, EventType
from .core import node

logger = logging.getLogger(__name__)


@node.processor.register_handler(HandlerType.Network, rid_types=[KoiNetNode])
def handshake_handler(proc: ProcessorInterface, kobj: KnowledgeObject):    
    logger.info("Handling node handshake")

    # only respond if node declares itself as NEW
    if kobj.event_type != EventType.NEW:
        return
        
    logger.info("Sharing this node's bundle with peer")
    proc.network.push_event_to(
        event=Event.from_bundle(EventType.NEW, proc.identity.bundle),
        node=kobj.rid,
        flush=True
    )
    
    logger.info("Proposing new edge")
    edge_bundle = Bundle.generate(
        KoiNetEdge.generate(kobj.rid, proc.identity.rid),
        EdgeModel(
            source=kobj.rid,
            target=proc.identity.rid,
            edge_type=EdgeType.WEBHOOK,
            rid_types=[KoiNetNode, KoiNetEdge],
            status=EdgeStatus.PROPOSED
        ).model_dump()
    )
        
    # proc.network.push_event_to(
    #     event=Event.from_bundle(EventType.NEW, edge_bundle),
    #     node=ievent.rid,
    #     flush=True
    # )
    
    proc.handle(bundle=edge_bundle)
