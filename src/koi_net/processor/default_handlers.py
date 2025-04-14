"""Provides implementations of default knowledge handlers."""

import logging
from rid_lib.ext.bundle import Bundle
from rid_lib.types import KoiNetNode, KoiNetEdge
from koi_net.protocol.node import NodeType
from .interface import ProcessorInterface
from .handler import KnowledgeHandler, HandlerType, STOP_CHAIN
from .knowledge_object import KnowledgeObject, KnowledgeSource
from ..protocol.event import Event, EventType
from ..protocol.edge import EdgeProfile, EdgeStatus, EdgeType

logger = logging.getLogger(__name__)

# RID handlers

@KnowledgeHandler.create(HandlerType.RID)
def basic_rid_handler(processor: ProcessorInterface, kobj: KnowledgeObject):
    """Default RID handler.
    
    Blocks external events about this node. Allows `FORGET` events if RID is known to this node.
    """
    if (kobj.rid == processor.identity.rid and 
        kobj.source == KnowledgeSource.External):
        logger.debug("Don't let anyone else tell me who I am!")
        return STOP_CHAIN
    
    if kobj.event_type == EventType.FORGET:
        kobj.normalized_event_type = EventType.FORGET
        return kobj

# Manifest handlers

@KnowledgeHandler.create(HandlerType.Manifest)
def basic_manifest_handler(processor: ProcessorInterface, kobj: KnowledgeObject):
    """Default manifest handler.
    
    Blocks manifests with the same hash, or aren't newer than the cached version. Sets the normalized event type to `NEW` or `UPDATE` depending on whether the RID was previously known to this node.
    """
    prev_bundle = processor.cache.read(kobj.rid)

    if prev_bundle:
        if kobj.manifest.sha256_hash == prev_bundle.manifest.sha256_hash:
            logger.debug("Hash of incoming manifest is same as existing knowledge, ignoring")
            return STOP_CHAIN
        if kobj.manifest.timestamp <= prev_bundle.manifest.timestamp:
            logger.debug("Timestamp of incoming manifest is the same or older than existing knowledge, ignoring")
            return STOP_CHAIN
        
        logger.debug("RID previously known to me, labeling as 'UPDATE'")
        kobj.normalized_event_type = EventType.UPDATE

    else:
        logger.debug("RID previously unknown to me, labeling as 'NEW'")
        kobj.normalized_event_type = EventType.NEW
        
    return kobj


# Bundle handlers

@KnowledgeHandler.create(
    handler_type=HandlerType.Bundle, 
    rid_types=[KoiNetEdge], 
    source=KnowledgeSource.External,
    event_types=[EventType.NEW, EventType.UPDATE])
def edge_negotiation_handler(processor: ProcessorInterface, kobj: KnowledgeObject):
    """Handles basic edge negotiation process.
    
    Automatically approves proposed edges if they request RID types this node can provide (or KOI nodes/edges). Validates the edge type is allowed for the node type (partial nodes cannot use webhooks). If edge is invalid, a `FORGET` event is sent to the other node.
    """
    
    edge_profile = EdgeProfile.model_validate(kobj.contents)

    # indicates peer subscribing to me
    if edge_profile.source == processor.identity.rid:     
        if edge_profile.status != EdgeStatus.PROPOSED:
            return
        
        logger.debug("Handling edge negotiation")
        
        peer_rid = edge_profile.target
        peer_profile = processor.network.graph.get_node_profile(peer_rid)
        
        if not peer_profile:
            logger.warning(f"Peer {peer_rid} unknown to me")
            return STOP_CHAIN
        
        # explicitly provided event RID types and (self) node + edge objects
        provided_events = (
            *processor.identity.profile.provides.event,
            KoiNetNode, KoiNetEdge
        )
        
        
        abort = False
        if (edge_profile.edge_type == EdgeType.WEBHOOK and 
            peer_profile.node_type == NodeType.PARTIAL):
            logger.debug("Partial nodes cannot use webhooks")
            abort = True
        
        if not set(edge_profile.rid_types).issubset(provided_events):
            logger.debug("Requested RID types not provided by this node")
            abort = True
        
        if abort:
            event = Event.from_rid(EventType.FORGET, kobj.rid)
            processor.network.push_event_to(event, peer_rid, flush=True)
            return STOP_CHAIN

        else:
            # approve edge profile
            logger.debug("Approving proposed edge")
            edge_profile.status = EdgeStatus.APPROVED
            updated_bundle = Bundle.generate(kobj.rid, edge_profile.model_dump())
      
            processor.handle(bundle=updated_bundle, event_type=EventType.UPDATE)
            return
              
    elif edge_profile.target == processor.identity.rid:
        if edge_profile.status == EdgeStatus.APPROVED:
            logger.debug("Edge approved by other node!")


# Network handlers

@KnowledgeHandler.create(HandlerType.Network)
def basic_network_output_filter(processor: ProcessorInterface, kobj: KnowledgeObject):
    """Default network handler.
    
    Allows broadcasting of all RID types this node is an event provider for (set in node profile), and other nodes have subscribed to. All nodes will also broadcast about their own (internally sourced) KOI node, and KOI edges that they are part of, regardless of their node profile configuration. Finally, nodes will also broadcast about edges to the other node involved (regardless of if they are subscribed)."""
    
    involves_me = False
    if kobj.source == KnowledgeSource.Internal:
        if (type(kobj.rid) == KoiNetNode):
            if (kobj.rid == processor.identity.rid):
                involves_me = True
        
        elif type(kobj.rid) == KoiNetEdge:
            edge_profile = kobj.bundle.validate_contents(EdgeProfile)
            
            if edge_profile.source == processor.identity.rid:
                logger.debug(f"Adding edge target '{edge_profile.target!r}' to network targets")
                kobj.network_targets.update([edge_profile.target])
                involves_me = True
                
            elif edge_profile.target == processor.identity.rid:
                logger.debug(f"Adding edge source '{edge_profile.source!r}' to network targets")
                kobj.network_targets.update([edge_profile.source])
                involves_me = True
    
    if (type(kobj.rid) in processor.identity.profile.provides.event or involves_me):
        # broadcasts to subscribers if I'm an event provider of this RID type OR it involves me
        subscribers = processor.network.graph.get_neighbors(
            direction="out",
            allowed_type=type(kobj.rid)
        )
        
        logger.debug(f"Updating network targets with '{type(kobj.rid)}' subscribers: {subscribers}")
        kobj.network_targets.update(subscribers)
        
    return kobj
            