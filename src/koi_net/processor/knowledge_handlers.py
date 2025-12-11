"""Implementation of default knowledge handlers."""

import structlog
from rid_lib.ext import Bundle
from rid_lib.ext.utils import sha256_hash
from rid_lib.types import KoiNetNode, KoiNetEdge

from ..exceptions import RequestError
from ..protocol.node import NodeType
from ..protocol.event import Event, EventType
from ..protocol.edge import EdgeProfile, EdgeStatus, EdgeType, generate_edge_bundle
from ..protocol.node import NodeProfile
from .handler import KnowledgeHandler, HandlerType, STOP_CHAIN
from .knowledge_object import KnowledgeObject
from .context import HandlerContext

log = structlog.stdlib.get_logger()


# RID handlers

@KnowledgeHandler.create(HandlerType.RID)
def basic_rid_handler(ctx: HandlerContext, kobj: KnowledgeObject):
    """Default RID handler.
    
    Blocks external events about this node. Sets normalized event type
    for `FORGET` events.
    """
    
    if (kobj.rid == ctx.identity.rid and kobj.source is not None):
        log.debug("Externally sourced events about this node not allowed.")
        return STOP_CHAIN
    
    if kobj.event_type == EventType.FORGET:
        kobj.normalized_event_type = EventType.FORGET
        return kobj


# Manifest handlers

@KnowledgeHandler.create(HandlerType.Manifest)
def basic_manifest_handler(ctx: HandlerContext, kobj: KnowledgeObject):
    """Normalized event decider based on manifest and cache state.
    
    Stops processing for manifests which have the same hash, or aren't 
    newer than the cached version. Sets the normalized event type to 
    `NEW` or `UPDATE` depending on whether the RID was previously known.
    """
    
    prev_bundle = ctx.cache.read(kobj.rid)

    if prev_bundle:
        if kobj.manifest.sha256_hash == prev_bundle.manifest.sha256_hash:
            log.debug("Hash of incoming manifest is same as existing knowledge, ignoring")
            return STOP_CHAIN
        if kobj.manifest.timestamp <= prev_bundle.manifest.timestamp:
            log.debug("Timestamp of incoming manifest is the same or older than existing knowledge, ignoring")
            return STOP_CHAIN
        
        log.debug("RID previously known to me, labeling as 'UPDATE'")
        kobj.normalized_event_type = EventType.UPDATE

    else:
        log.debug("RID previously unknown to me, labeling as 'NEW'")
        kobj.normalized_event_type = EventType.NEW
        
    return kobj


# Bundle handlers

@KnowledgeHandler.create(
    handler_type=HandlerType.Bundle,
    rid_types=(KoiNetNode,),
    event_types=(EventType.NEW, EventType.UPDATE))
def secure_profile_handler(ctx: HandlerContext, kobj: KnowledgeObject):
    """Maintains security of cached node profiles.
    
    Blocks bundles with a mismatching public keys in their node profile
    and RID from being written to cache.
    """
    
    node_profile = kobj.bundle.validate_contents(NodeProfile)
    node_rid: KoiNetNode = kobj.rid
    
    if sha256_hash(node_profile.public_key) != node_rid.hash:
        log.warning(f"Public key hash mismatch for {node_rid!r}!")
        return STOP_CHAIN

@KnowledgeHandler.create(
    handler_type=HandlerType.Bundle, 
    rid_types=(KoiNetEdge,), 
    event_types=(EventType.NEW, EventType.UPDATE))
def edge_negotiation_handler(ctx: HandlerContext, kobj: KnowledgeObject):
    """Handles edge negotiation process.
    
    Automatically approves proposed edges if they request RID types this 
    node can provide (or KOI node, edge RIDs). Validates the edge type 
    is allowed for the node type (partial nodes cannot use webhooks). If 
    edge is invalid, a `FORGET` event is sent to the other node.
    """

    # only handle incoming events (ignore internal edge knowledge objects)
    if kobj.source is None: 
        return
    
    edge_profile = kobj.bundle.validate_contents(EdgeProfile)

    # indicates peer subscribing to this node
    if edge_profile.source == ctx.identity.rid:
        if edge_profile.status != EdgeStatus.PROPOSED:
            return
        
        log.debug("Handling edge negotiation")
        
        peer_rid = edge_profile.target
        peer_bundle = ctx.cache.read(peer_rid)
        
        if not peer_bundle:
            log.warning(f"Peer {peer_rid!r} unknown to me")
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
            log.debug("Partial nodes cannot use webhooks")
            abort = True
        
        if not set(edge_profile.rid_types).issubset(provided_events):
            log.debug("Requested RID types not provided by this node")
            abort = True
        
        if abort:
            event = Event.from_rid(EventType.FORGET, kobj.rid)
            ctx.event_queue.push(event, peer_rid, flush=True)
            return STOP_CHAIN
        
        else:
            log.debug("Approving proposed edge")
            edge_profile.status = EdgeStatus.APPROVED
            updated_bundle = Bundle.generate(kobj.rid, edge_profile.model_dump())
      
            ctx.kobj_queue.push(bundle=updated_bundle, event_type=EventType.UPDATE)
            return
              
    elif edge_profile.target == ctx.identity.rid:
        if edge_profile.status == EdgeStatus.APPROVED:
            log.debug("Edge approved by other node!")


# Network handlers

@KnowledgeHandler.create(HandlerType.Network, rid_types=(KoiNetNode,))
def node_contact_handler(ctx: HandlerContext, kobj: KnowledgeObject):
    """Makes contact with providers of RID types of interest.
    
    When an incoming node knowledge object is identified as a provider
    of an RID type of interest, this handler will propose a new edge 
    subscribing to future node events, and fetch existing nodes to catch 
    up to the current state.
    """
    # prevents nodes from attempting to form a self loop
    if kobj.rid == ctx.identity.rid:
        return
    
    node_profile = kobj.bundle.validate_contents(NodeProfile)
    
    available_rid_types = list(
        set(ctx.config.koi_net.rid_types_of_interest) & 
        set(node_profile.provides.event)
    )
    
    if not available_rid_types:
        return
    
    edge_rid = ctx.graph.get_edge(
        source=kobj.rid,
        target=ctx.identity.rid,
    )
    
    # already have an edge established
    if edge_rid:
        prev_edge_bundle = ctx.cache.read(edge_rid)
        edge_profile = prev_edge_bundle.validate_contents(EdgeProfile)
        
        if set(edge_profile.rid_types) == set(available_rid_types):
            # no change in rid types
            return
        
        log.info(f"Proposing updated edge with node provider {available_rid_types}")
        
        edge_profile.rid_types = available_rid_types
        edge_profile.status = EdgeStatus.PROPOSED
        edge_bundle = Bundle.generate(edge_rid, edge_profile.model_dump())
    
    # no existing edge
    else:
        log.info(f"Proposing new edge with node provider {available_rid_types}")
        edge_bundle = generate_edge_bundle(
            source=kobj.rid,
            target=ctx.identity.rid,
            rid_types=available_rid_types,
            edge_type=(
                EdgeType.WEBHOOK
                if ctx.identity.profile.node_type == NodeType.FULL
                else EdgeType.POLL
            )
        )
    
    # queued for processing
    ctx.kobj_queue.push(bundle=edge_bundle)
    
    log.info("Catching up on network state")
    try:
        payload = ctx.request_handler.fetch_rids(
            node=kobj.rid, 
            rid_types=available_rid_types
        )
    except RequestError:
        log.info("Failed to reach node")
        return
        
    for rid in payload.rids:
        if rid == ctx.identity.rid:
            log.info("Skipping myself")
            continue
        if ctx.cache.exists(rid):
            log.info(f"Skipping known RID {rid!r}")
            continue
        
        # marked as external since we are handling RIDs from another node
        # will fetch remotely instead of checking local cache
        ctx.kobj_queue.push(rid=rid, source=kobj.rid)
    log.info("Done")

@KnowledgeHandler.create(HandlerType.Network)
def basic_network_output_filter(ctx: HandlerContext, kobj: KnowledgeObject):
    """Sets network targets of outgoing event for knowledge object.
    
    Allows broadcasting of all RID types this node is an event provider 
    for (set in node profile), and other nodes have subscribed to. All 
    nodes will also broadcast events about their own (internally sourced) 
    KOI node, and KOI edges that they are part of, regardless of their 
    node profile configuration. Finally, nodes will also broadcast about 
    edges to the other node involved (regardless of if they are subscribed).
    """
    
    involves_this_node = False
    # internally source knowledge objects
    if kobj.source is None:
        if type(kobj.rid) is KoiNetNode:
            if (kobj.rid == ctx.identity.rid):
                involves_this_node = True
        
        elif type(kobj.rid) is KoiNetEdge:
            edge_profile = kobj.bundle.validate_contents(EdgeProfile)
            
            if edge_profile.source == ctx.identity.rid:
                log.debug(f"Adding edge target '{edge_profile.target!r}' to network targets")
                kobj.network_targets.add(edge_profile.target)
                involves_this_node = True
                
            elif edge_profile.target == ctx.identity.rid:
                log.debug(f"Adding edge source '{edge_profile.source!r}' to network targets")
                kobj.network_targets.add(edge_profile.source)
                involves_this_node = True
    
    if (type(kobj.rid) in ctx.identity.profile.provides.event or involves_this_node):
        subscribers = ctx.graph.get_neighbors(
            direction="out",
            allowed_type=type(kobj.rid)
        )
        
        log.debug(f"Updating network targets with '{type(kobj.rid)}' subscribers: {subscribers}")
        kobj.network_targets.update(subscribers)
        
    return kobj

@KnowledgeHandler.create(HandlerType.Final, rid_types=[KoiNetNode])
def forget_edge_on_node_deletion(ctx: HandlerContext, kobj: KnowledgeObject):
    """Removes edges to forgotten nodes."""
    
    if kobj.normalized_event_type != EventType.FORGET:
        return
    
    for edge_rid in ctx.graph.get_edges():
        edge_bundle = ctx.cache.read(edge_rid)
        if not edge_bundle:
            continue
        edge_profile = edge_bundle.validate_contents(EdgeProfile)
        
        if kobj.rid in (edge_profile.source, edge_profile.target):
            log.debug("Identified edge with forgotten node")
            ctx.kobj_queue.push(rid=edge_rid, event_type=EventType.FORGET)