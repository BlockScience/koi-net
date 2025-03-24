import logging
from rid_lib.types import KoiNetNode, KoiNetEdge
from rid_lib.ext import Event, EventType, Bundle
from koi_net.processor import ProcessorInterface
from koi_net.models import EdgeModel, NormalizedType
from .core import node, this_node_profile

logger = logging.getLogger(__name__)


@node.processor.register_event_handler(rid_types=[KoiNetNode])
def handshake_handler(proc: ProcessorInterface, event: Event, event_type: NormalizedType):    
    logger.info("Handling node handshake")

    # only respond if node is unknown to me
    if event_type != EventType.NEW:
        logger.info("Peer already know to this node, ignoring")
        return
    
    my_bundle = proc.cache.read(node.network.me)
    
    logger.info("Sharing this node's bundle with peer")
    proc.network.push_event_to(
        event=Event.from_bundle(EventType.NEW, my_bundle),
        node=event.rid,
        flush=True
    )
    
    logger.info("Proposing new edge")
    edge_bundle = Bundle.generate(
        KoiNetEdge("partial->coordinator"),
        EdgeModel(
            source=event.rid,
            target=proc.network.me,
            comm_type="webhook",
            rid_types=[KoiNetNode, KoiNetEdge],
            status="proposed"
        ).model_dump()
    )
        
    proc.network.push_event_to(
        event=Event.from_manifest(EventType.NEW, edge_bundle.manifest),
        node=event.rid,
        flush=True
    )
    proc.handle_state(edge_bundle)

    
@node.processor.register_event_handler(rid_types=[KoiNetEdge])
def edge_negotiation_handler(processor: ProcessorInterface, event: Event, event_type: NormalizedType):
    bundle = event.bundle or processor.cache.read(event.rid)
    edge_profile = EdgeModel.model_validate(bundle.contents)

    logger.info("Handling edge negotiation")

    # indicates peer subscriber
    if edge_profile.source == processor.network.me:                
        if edge_profile.status != "proposed":
            # TODO: handle other status
            return
        
        if any(rid_type not in this_node_profile.provides.event for rid_type in edge_profile.rid_types):
            # indicates node subscribing to unsupported event
            # TODO: either reject or repropose agreement
            logger.info("Requested RID types not provided by this node")
            event = Event.from_rid(EventType.FORGET, event.rid)

            
        elif not processor.cache.read(edge_profile.target):
            # TODO: handle unknown subscriber node (delete edge?)
            logger.warning("Peer unknown to this node")
            event = Event.from_bundle(EventType.FORGET, event.rid)

        else:
            # approve edge profile
            edge_profile.status = "approved"
            updated_bundle = Bundle.generate(bundle.manifest.rid, edge_profile.model_dump())
            
            event = Event.from_bundle(EventType.UPDATE, updated_bundle)
            
        processor.network.push_event_to(event, edge_profile.target, flush=True)
        processor.handle_event(event)
        
    elif edge_profile.target == processor.network.me:
        logger.info("Edge approved by other node!")