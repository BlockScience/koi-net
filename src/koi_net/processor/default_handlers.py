import logging
from rid_lib.ext.bundle import Bundle
from rid_lib.types import KoiNetNode, KoiNetEdge
from .interface import ProcessorInterface
from .handler import HandlerType, STOP_CHAIN
from .knowledge_object import KnowledgeObject, KnowledgeSource
from ..protocol.event import Event, EventType
from ..protocol.edge import EdgeModel,EdgeStatus

logger = logging.getLogger(__name__)

# RID handlers

@ProcessorInterface.as_handler(handler_type=HandlerType.RID)
def basic_rid_handler(processor: ProcessorInterface, kobj: KnowledgeObject):
    if (kobj.rid == processor.identity.rid and 
        kobj.source == KnowledgeSource.External):
        logger.info("Don't let anyone else tell me who I am!")
        return STOP_CHAIN
    
    if kobj.event_type == EventType.FORGET:        
        if processor.cache.exists(kobj.rid):
            logger.info("Allowing cache forget")
            kobj.normalized_event_type = EventType.FORGET
            return kobj
        
        else:
            # can't forget something I don't know about
            return STOP_CHAIN


# Manifest handlers

@ProcessorInterface.as_handler(handler_type=HandlerType.Manifest)
def basic_state_handler(processor: ProcessorInterface, kobj: KnowledgeObject):
    prev_bundle = processor.cache.read(kobj.rid)

    if prev_bundle:
        if kobj.manifest.sha256_hash == prev_bundle.manifest.sha256_hash:
            logger.info("Hash of incoming manifest is same as existing knowledge, ignoring")
            return STOP_CHAIN
        if kobj.manifest.timestamp <= prev_bundle.manifest.timestamp:
            logger.info("Timestamp of incoming manifest is the same or older than existing knowledge, ignoring")
            return STOP_CHAIN
        
        logger.info("RID previously known to me, labeling as 'UPDATE'")
        kobj.normalized_event_type = EventType.UPDATE

    else:
        logger.info("RID previously unknown to me, labeling as 'NEW'")
        kobj.normalized_event_type = EventType.NEW
        
    return kobj


# Bundle handlers

@ProcessorInterface.as_handler(HandlerType.Bundle, rid_types=[KoiNetEdge])
def edge_negotiation_handler(processor: ProcessorInterface, kobj: KnowledgeObject):
    edge_profile = EdgeModel.model_validate(kobj.contents)
    
    # only want to handle external knowledge events (not edges this node created)
    if kobj.source != KnowledgeSource.External:
        return

    # indicates peer subscribing to me
    if edge_profile.source == processor.identity.rid:     
        if edge_profile.status != EdgeStatus.PROPOSED:
            return
        
        logger.info("Handling edge negotiation")
        
        peer_rid = edge_profile.target
        
        if not processor.cache.exists(peer_rid):
            logger.warning(f"Peer {peer_rid} unknown to this node")
            return STOP_CHAIN
        
        # explicitly provided event RID types and (self) node + edge objects
        provided_events = (
            *processor.identity.profile.provides.event,
            KoiNetNode, KoiNetEdge
        )
        
        if not set(edge_profile.rid_types).issubset(provided_events):
            logger.info("Requested RID types not provided by this node")
            event = Event.from_rid(EventType.FORGET, kobj.rid)
            processor.network.push_event_to(event, peer_rid, flush=True)
            
            return STOP_CHAIN

        else:
            # approve edge profile
            logger.info("Approving proposed edge")
            edge_profile.status = EdgeStatus.APPROVED
            updated_bundle = Bundle.generate(kobj.rid, edge_profile.model_dump())
      
            processor.handle(bundle=updated_bundle)
            return
              
    elif edge_profile.target == processor.identity.rid:
        if edge_profile.status == EdgeStatus.APPROVED:
            logger.info("Edge approved by other node!")


# Network handlers

@ProcessorInterface.as_handler(HandlerType.Network)
def basic_network_output_filter(processor: ProcessorInterface, kobj: KnowledgeObject):    
    if type(kobj.rid) not in processor.identity.profile.provides.event:
        if kobj.source == KnowledgeSource.External:
            logger.info("I don't provide events for this RID type")
            return
    
        if type(kobj.rid) == KoiNetNode:
            if kobj.rid != processor.identity.rid:
                logger.info("I only share my own node profile")
                return
            
        elif type(kobj.rid) == KoiNetEdge:
            if kobj.bundle:
                edge_profile = kobj.bundle.validate_contents(EdgeModel)
                if processor.identity.rid not in (edge_profile.source, edge_profile.target):            
                    logger.info("I only share edges I am a part of")
                    
        else:
            logger.info("I don't provide events for this RID type")
            return
    
    subscribers = processor.network.graph.get_neighbors(
        direction="out",
        allowed_type=type(kobj.rid)
    )
    
    logger.info(f"Updating network targets with '{type(kobj.rid)}' subscribers: {subscribers}")
    kobj.network_targets.update(subscribers)
    
    # add peer node in edge to network targets
    if type(kobj.rid) == KoiNetEdge and kobj.source == KnowledgeSource.Internal:
        if kobj.bundle:
            edge_profile = kobj.bundle.validate_contents(EdgeModel)
            
            if edge_profile.source == processor.identity.rid:
                logger.info(f"Adding edge target '{edge_profile.target}' to network targets")
                kobj.network_targets.update([edge_profile.target])
                
            elif edge_profile.target == processor.identity.rid:
                kobj.network_targets.update([edge_profile.source])
                logger.info(f"Adding edge source '{edge_profile.source}' to network targets")
        
    return kobj
            