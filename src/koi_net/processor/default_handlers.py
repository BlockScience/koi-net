import logging
from rid_lib.types import KoiNetNode, KoiNetEdge
from .interface import ProcessorInterface
from .handler import HandlerType, InternalEvent, STOP_CHAIN
from ..protocol.event import Event, EventType
from ..protocol.edge import EdgeModel,EdgeStatus

logger = logging.getLogger(__name__)

@ProcessorInterface.as_handler(handler_type=HandlerType.RID)
def basic_rid_handler(processor: ProcessorInterface, ievent: InternalEvent):
    if ievent.event_type == EventType.FORGET:
        logger.info("Allowing cache forget")
        ievent.normalized_event_type = EventType.FORGET
        return ievent


@ProcessorInterface.as_handler(handler_type=HandlerType.Manifest)
def basic_state_handler(processor: ProcessorInterface, ievent: InternalEvent):
    prev_bundle = processor.cache.read(ievent.rid)

    if prev_bundle:
        if ievent.manifest.sha256_hash == prev_bundle.manifest.sha256_hash:
            logger.info("Hash of incoming manifest is same as existing knowledge, ignoring")
            return STOP_CHAIN # same knowledge
        if ievent.manifest.timestamp <= prev_bundle.manifest.timestamp:
            logger.info("Timestamp of incoming manifest is older than existing knowledge, ignoring")
            return STOP_CHAIN # incoming state is older
        
        logger.info("RID previously known to me, labeling as 'UPDATE'")
        ievent.normalized_event_type = EventType.UPDATE

    else:
        logger.info("RID previously unknown to me, labeling as 'NEW'")
        ievent.normalized_event_type = EventType.NEW
        
    return ievent # must return ievent


@ProcessorInterface.as_handler(HandlerType.Bundle, rid_types=[KoiNetEdge])
def edge_negotiation_handler(processor: ProcessorInterface, ievent: InternalEvent):
    edge_profile = EdgeModel.model_validate(ievent.contents)

    logger.info("Handling edge negotiation")

    # indicates peer subscriber
    if edge_profile.source == processor.identity.rid:                
        if edge_profile.status != EdgeStatus.PROPOSED:
            # TODO: handle other status
            return
        
        peer_rid = edge_profile.target
        
        if not processor.cache.exists(peer_rid):
            logger.warning(f"Peer {peer_rid} unknown to this node")
            return STOP_CHAIN
        
        if not set(edge_profile.rid_types).issubset(
            processor.identity.profile.provides.event +
            processor.identity.implicitly_provides.event
        ):
            # indicates node subscribing to unsupported event
            # TODO: either reject or repropose agreement
            logger.info("Requested RID types not provided by this node")            
            event = Event.from_rid(EventType.FORGET, ievent.rid)
            processor.network.push_event_to(event, peer_rid, flush=True)
            
            return STOP_CHAIN

        else:
            # approve edge profile
            edge_profile.status = EdgeStatus.APPROVED
            logger.info("Approving proposed edge")
            
            ievent.update_contents(edge_profile.model_dump())
            event = Event.from_bundle(EventType.UPDATE, ievent.bundle)
            processor.network.push_event_to(event, peer_rid, flush=True)
            return ievent
        
    elif edge_profile.target == processor.identity.rid:
        if edge_profile.status == EdgeStatus.APPROVED:
            logger.info("Edge approved by other node!")

@ProcessorInterface.as_handler(HandlerType.Network)
def basic_network_output_filter(processor: ProcessorInterface, ievent: InternalEvent):
    rid_type = type(ievent.rid)
    if rid_type not in processor.identity.profile.provides.event:
        if rid_type not in processor.identity.implicitly_provides.event:
            logger.info(f"I don't provide events for '{type(ievent.rid)}', blocking broadcast")
            return STOP_CHAIN

        elif rid_type == KoiNetNode:
            if ievent.rid != processor.identity.rid:
                logger.info("Blocking broadcast of another node")
                return STOP_CHAIN
            
        elif rid_type == KoiNetEdge:
            # edge_profile = ievent.bundle.validate_contents(EdgeModel)
            # if processor.identity.rid not in (edge_profile.source, edge_profile.target):
            
            if ievent.rid not in processor.network.graph.get_edges():
                logger.info("Blocking broadcast of edge I don't belong to")
                return STOP_CHAIN
            