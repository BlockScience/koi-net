"""Provides implementations of default knowledge handlers."""

import logging
from rid_lib.ext import Bundle
from rid_lib.ext.utils import sha256_hash
from rid_lib.types import KoiNetNode, KoiNetEdge
from koi_net.protocol.node import NodeType
from .handler import KnowledgeHandler, HandlerType, STOP_CHAIN
from .knowledge_object import KnowledgeObject
from ..context import HandlerContext
from ..protocol.event import Event, EventType
from ..protocol.edge import EdgeProfile, EdgeStatus, EdgeType, generate_edge_bundle
from ..protocol.node import NodeProfile

logger = logging.getLogger(__name__)

# RID handlers

@KnowledgeHandler.create(HandlerType.RID)
def basic_rid_handler(ctx: HandlerContext, kobj: KnowledgeObject):
    """Default RID handler.
    
    Blocks external events about this node. Allows `FORGET` events if RID is known to this node.
    """
    if (kobj.rid == ctx.identity.rid and kobj.source):
        logger.debug("Don't let anyone else tell me who I am!")
        return STOP_CHAIN
    
    if kobj.event_type == EventType.FORGET:
        kobj.normalized_event_type = EventType.FORGET
        return kobj

# Manifest handlers

@KnowledgeHandler.create(HandlerType.Manifest)
def basic_manifest_handler(ctx: HandlerContext, kobj: KnowledgeObject):
    """Default manifest handler.
    
    Blocks manifests with the same hash, or aren't newer than the cached version. Sets the normalized event type to `NEW` or `UPDATE` depending on whether the RID was previously known to this node.
    """
    prev_bundle = ctx.cache.read(kobj.rid)

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
    rid_types=[KoiNetNode],
    event_types=[EventType.NEW, EventType.UPDATE]
)
def secure_profile_handler(ctx: HandlerContext, kobj: KnowledgeObject):
    node_profile = kobj.bundle.validate_contents(NodeProfile)
    node_rid: KoiNetNode = kobj.rid
    
    if sha256_hash(node_profile.public_key) != node_rid.hash:
        logger.warning(f"Public key hash mismatch for {node_rid!r}!")
        return STOP_CHAIN

@KnowledgeHandler.create(
    handler_type=HandlerType.Bundle, 
    rid_types=[KoiNetEdge], 
    event_types=[EventType.NEW, EventType.UPDATE])
def edge_negotiation_handler(ctx: HandlerContext, kobj: KnowledgeObject):
    """Handles basic edge negotiation process.
    
    Automatically approves proposed edges if they request RID types this node can provide (or KOI nodes/edges). Validates the edge type is allowed for the node type (partial nodes cannot use webhooks). If edge is invalid, a `FORGET` event is sent to the other node.
    """

    # only respond when source is another node
    if kobj.source is None: return
    
    edge_profile = kobj.bundle.validate_contents(EdgeProfile)

    # indicates peer subscribing to me
    if edge_profile.source == ctx.identity.rid:     
        if edge_profile.status != EdgeStatus.PROPOSED:
            return
        
        logger.debug("Handling edge negotiation")
        
        peer_rid = edge_profile.target
        peer_bundle = ctx.effector.deref(peer_rid)
        
        if not peer_bundle:
            logger.warning(f"Peer {peer_rid!r} unknown to me")
            return STOP_CHAIN
        
        peer_profile = peer_bundle.validate_contents(NodeProfile)
        
        # explicitly provided event RID types and (self) node + edge objects
        provided_events = (
            *ctx.identity.profile.provides.event,
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
            ctx.event_queue.push_event_to(event, peer_rid, flush=True)
            return STOP_CHAIN

        else:
            # approve edge profile
            logger.debug("Approving proposed edge")
            edge_profile.status = EdgeStatus.APPROVED
            updated_bundle = Bundle.generate(kobj.rid, edge_profile.model_dump())
      
            ctx.handle(bundle=updated_bundle, event_type=EventType.UPDATE)
            return
              
    elif edge_profile.target == ctx.identity.rid:
        if edge_profile.status == EdgeStatus.APPROVED:
            logger.debug("Edge approved by other node!")


# Network handlers

@KnowledgeHandler.create(HandlerType.Network, rid_types=[KoiNetNode])
def coordinator_contact(ctx: HandlerContext, kobj: KnowledgeObject):
    node_profile = kobj.bundle.validate_contents(NodeProfile)
            
    # looking for event provider of nodes
    if KoiNetNode not in node_profile.provides.event:
        return
    
    # prevents coordinators from attempting to form a self loop
    if kobj.rid == ctx.identity.rid:
        return
    
    # already have an edge established
    if ctx.graph.get_edge(
        source=kobj.rid,
        target=ctx.identity.rid,
    ) is not None:
        return
    
    logger.info("Identified a coordinator!")
    logger.info("Proposing new edge")
    
    if ctx.identity.profile.node_type == NodeType.FULL:
        edge_type = EdgeType.WEBHOOK
    else:
        edge_type = EdgeType.POLL
    
    # queued for processing
    ctx.handle(bundle=generate_edge_bundle(
        source=kobj.rid,
        target=ctx.identity.rid,
        edge_type=edge_type,
        rid_types=[KoiNetNode]
    ))
    
    logger.info("Catching up on network state")
    
    payload = ctx.request_handler.fetch_rids(
        node=kobj.rid, 
        rid_types=[KoiNetNode]
    )
    for rid in payload.rids:
        if rid == ctx.identity.rid:
            logger.info("Skipping myself")
            continue
        if ctx.cache.exists(rid):
            logger.info(f"Skipping known RID {rid!r}")
            continue
        
        # marked as external since we are handling RIDs from another node
        # will fetch remotely instead of checking local cache
        ctx.handle(rid=rid, source=kobj.rid)
    logger.info("Done")
    

@KnowledgeHandler.create(HandlerType.Network)
def basic_network_output_filter(ctx: HandlerContext, kobj: KnowledgeObject):
    """Default network handler.
    
    Allows broadcasting of all RID types this node is an event provider for (set in node profile), and other nodes have subscribed to. All nodes will also broadcast about their own (internally sourced) KOI node, and KOI edges that they are part of, regardless of their node profile configuration. Finally, nodes will also broadcast about edges to the other node involved (regardless of if they are subscribed)."""
    
    involves_me = False
    if kobj.source is None:
        if (type(kobj.rid) == KoiNetNode):
            if (kobj.rid == ctx.identity.rid):
                involves_me = True
        
        elif type(kobj.rid) == KoiNetEdge:
            edge_profile = kobj.bundle.validate_contents(EdgeProfile)
            
            if edge_profile.source == ctx.identity.rid:
                logger.debug(f"Adding edge target '{edge_profile.target!r}' to network targets")
                kobj.network_targets.update([edge_profile.target])
                involves_me = True
                
            elif edge_profile.target == ctx.identity.rid:
                logger.debug(f"Adding edge source '{edge_profile.source!r}' to network targets")
                kobj.network_targets.update([edge_profile.source])
                involves_me = True
    
    if (type(kobj.rid) in ctx.identity.profile.provides.event or involves_me):
        # broadcasts to subscribers if I'm an event provider of this RID type OR it involves me
        subscribers = ctx.graph.get_neighbors(
            direction="out",
            allowed_type=type(kobj.rid)
        )
        
        logger.debug(f"Updating network targets with '{type(kobj.rid)}' subscribers: {subscribers}")
        kobj.network_targets.update(subscribers)
        
    return kobj

@KnowledgeHandler.create(HandlerType.Final, rid_types=[KoiNetNode])
def forget_edge_on_node_deletion(ctx: HandlerContext, kobj: KnowledgeObject):
    if kobj.normalized_event_type != EventType.FORGET:
        return
    
    for edge_rid in ctx.graph.get_edges():
        edge_bundle = ctx.cache.read(edge_rid)
        if not edge_bundle: continue
        edge_profile = edge_bundle.validate_contents(EdgeProfile)
        
        if kobj.rid in (edge_profile.source, edge_profile.target):
            logger.debug("Identified edge with forgotten node")
            ctx.handle(rid=edge_rid, event_type=EventType.FORGET)