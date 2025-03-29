import logging
from rid_lib.types import KoiNetNode, KoiNetEdge
from .interface import ProcessorInterface
from .handler import KnowledgeSource, HandlerType, KnowledgeObject, STOP_CHAIN
from ..protocol.event import Event, EventType
from ..protocol.edge import EdgeModel,EdgeStatus

logger = logging.getLogger(__name__)

@ProcessorInterface.as_handler(handler_type=HandlerType.RID)
def basic_rid_handler(processor: ProcessorInterface, kobj: KnowledgeObject):
    if kobj.event_type == EventType.FORGET:
        logger.info("Allowing cache forget")
        kobj.normalized_event_type = EventType.FORGET
        return kobj


@ProcessorInterface.as_handler(handler_type=HandlerType.Manifest)
def basic_state_handler(processor: ProcessorInterface, kobj: KnowledgeObject):
    prev_bundle = processor.cache.read(kobj.rid)

    if prev_bundle:
        if kobj.manifest.sha256_hash == prev_bundle.manifest.sha256_hash:
            logger.info("Hash of incoming manifest is same as existing knowledge, ignoring")
            return STOP_CHAIN # same knowledge
        if kobj.manifest.timestamp <= prev_bundle.manifest.timestamp:
            logger.info("Timestamp of incoming manifest is older than existing knowledge, ignoring")
            return STOP_CHAIN # incoming state is older
        
        logger.info("RID previously known to me, labeling as 'UPDATE'")
        kobj.normalized_event_type = EventType.UPDATE

    else:
        logger.info("RID previously unknown to me, labeling as 'NEW'")
        kobj.normalized_event_type = EventType.NEW
        
    return kobj # must return kobj


@ProcessorInterface.as_handler(HandlerType.Bundle, rid_types=[KoiNetEdge])
def edge_negotiation_handler(processor: ProcessorInterface, kobj: KnowledgeObject):
    edge_profile = EdgeModel.model_validate(kobj.contents)

    logger.info("Handling edge negotiation")
    
    # only want to handle external knowledge events
    if kobj.source != KnowledgeSource.External:
        return

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
            event = Event.from_rid(EventType.FORGET, kobj.rid)
            processor.network.push_event_to(event, peer_rid, flush=True)
            
            return STOP_CHAIN

        else:
            # approve edge profile
            edge_profile.status = EdgeStatus.APPROVED
            logger.info("Approving proposed edge")
            
            kobj.update_contents(edge_profile.model_dump())
            event = Event.from_bundle(EventType.UPDATE, kobj.bundle)
            
            # queue UPDATE separate from NEW
            processor.handle_bundle(kobj.bundle, queue=True)
            return
            
            # process NEW -> UPDATE
            # return kobj
            
            # processor.network.push_event_to(event, peer_rid, flush=True)
            # return kobj
        
    elif edge_profile.target == processor.identity.rid:
        if edge_profile.status == EdgeStatus.APPROVED:
            logger.info("Edge approved by other node!")

@ProcessorInterface.as_handler(HandlerType.Network)
def basic_network_output_filter(processor: ProcessorInterface, kobj: KnowledgeObject):
    subscribers = processor.network.graph.get_neighbors(
        direction="out",
        allowed_type=type(kobj.rid)
    )
    
    rid_type = type(kobj.rid)
    
    # add subscribers to RID type to network targets
    if rid_type not in processor.identity.profile.provides.event:
        if rid_type not in processor.identity.implicitly_provides.event:
            logger.info(f"I don't provide events for '{type(kobj.rid)}', blocking broadcast")
            return

        elif rid_type == KoiNetNode:
            if kobj.rid != processor.identity.rid:
                logger.info("Blocking broadcast of another node")
                return
            
        elif rid_type == KoiNetEdge:
            # TODO: how to deal with FORGET events where we can't check the edge bundle
            
            # edge_profile = kobj.bundle.validate_contents(EdgeModel)
            # if processor.identity.rid not in (edge_profile.source, edge_profile.target):
            
            if kobj.rid not in processor.network.graph.get_edges():
                logger.info("Blocking broadcast of edge I don't belong to")
                return
    
    logger.info(f"Updating network targets with '{rid_type}' subscribers: {subscribers}")
    kobj.network_targets.update(subscribers)
    
    # add peer node in edge to network targets
    if rid_type == KoiNetEdge and kobj.event_type != EventType.FORGET:
        if kobj.source == KnowledgeSource.Internal:    
            edge_profile = kobj.bundle.validate_contents(EdgeModel)
            
            if edge_profile.source == processor.identity.rid:
                logger.info(f"Adding edge target '{edge_profile.target}' to network targets")
                kobj.network_targets.update([edge_profile.target])
                
            elif edge_profile.target == processor.identity.rid:
                kobj.network_targets.update([edge_profile.source])
                logger.info(f"Adding to edge source '{edge_profile.source}' to network targets")
        else:
            logger.info("Ignoring external edge event")
    return kobj
            