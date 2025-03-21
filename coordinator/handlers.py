import logging
from koi_net.models import EdgeModel, NormalizedType
from koi_net.rid_types import KoiNetNode, KoiNetEdge
from rid_lib.ext import Event, EventType, Bundle
from .core import node, this_node_profile

logger = logging.getLogger(__name__)


@node.processor.register_event_handler(contexts=[KoiNetNode])
def handshake_handler(event: Event, event_type: NormalizedType):    
    logger.info("Handling node handshake")

    # only respond if node is unknown to me
    if event_type != EventType.NEW:
        logger.info("Peer already know to this node, ignoring")
        return
    
    my_bundle = node.cache.read(node.network.me)
    
    logger.info("Sharing this node's bundle with peer")
    node.network.push_event_to(
        event=Event.from_bundle(EventType.NEW, my_bundle),
        node=event.rid,
        flush=True
    )
    
    logger.info("Proposing new edge")
    edge_bundle = Bundle.generate(
        KoiNetEdge("partial->coordinator"),
        EdgeModel(
            source=event.rid,
            target=node.network.me,
            comm_type="webhook",
            rid_types=[KoiNetNode, KoiNetEdge],
            status="proposed"
        ).model_dump()
    )
        
    node.network.push_event_to(
        event=Event.from_manifest(EventType.NEW, edge_bundle.manifest),
        node=event.rid,
        flush=True
    )
    node.processor.handle_state(edge_bundle)

    
@node.processor.register_event_handler(contexts=[KoiNetEdge])
def edge_negotiation_handler(event: Event, event_type: NormalizedType):
    bundle = event.bundle or node.cache.read(event.rid)
    edge_profile = EdgeModel.model_validate(bundle.contents)

    logger.info("Handling edge negotiation")

    # indicates peer subscriber
    if edge_profile.source == node.network.me:                
        if edge_profile.status != "proposed":
            # TODO: handle other status
            return
        
        if any(context not in this_node_profile.provides.event for context in edge_profile.rid_types):
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