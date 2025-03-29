import logging
from queue import Queue
from typing import Callable
from rid_lib.core import RID, RIDType
from rid_lib.ext import Bundle, Cache, Manifest
from rid_lib.types.koi_net_edge import KoiNetEdge
from rid_lib.types.koi_net_node import KoiNetNode
from ..identity import NodeIdentity
from ..network import NetworkInterface
from ..protocol.edge import EdgeModel
from ..protocol.event import Event, EventType
from .handler import (
    Handler, 
    HandlerType, 
    KnowledgeObject,
    KnowledgeSource, 
    KnowledgeEventType,
    STOP_CHAIN
)

logger = logging.getLogger(__name__)


class ProcessorInterface:
    cache: Cache
    network: NetworkInterface
    identity: NodeIdentity
    handlers: list[Handler]
    kobj_queue: Queue[KnowledgeObject]
    
    def __init__(
        self, 
        cache: Cache, 
        network: NetworkInterface,
        identity: NodeIdentity,
        default_handlers: list[Handler] = []
    ):
        self.cache = cache
        self.network = network
        self.identity = identity
        self.handlers: list[Handler] = default_handlers
        self.kobj_queue = Queue()
    
    @classmethod
    def as_handler(
        cls,
        handler_type: HandlerType,
        rid_types: list[RIDType] | None = None
    ):
        """Special decorator that returns a Handler instead of a function."""
        def decorator(func: Callable) -> Handler:
            handler = Handler(func, handler_type, rid_types, )
            return handler
        return decorator
            
    def register_handler(
        self,
        handler_type: HandlerType,
        rid_types: list[RIDType] | None = None
    ):
        """Assigns decorated function as handler for this Processor."""
        def decorator(func: Callable) -> Callable:
            handler = Handler(func, handler_type, rid_types)
            self.handlers.append(handler)
            return func
        return decorator
            
    def call_handler_chain(
        self, 
        handler_type: HandlerType,
        kobj: KnowledgeObject
    ):
        for handler in self.handlers:
            if handler_type != handler.handler_type: 
                continue
            
            if handler.rid_types and type(kobj.rid) not in handler.rid_types:
                continue
            
            logger.info(f"Calling {handler_type} handler '{handler.func.__name__}'")
            resp = handler.func(self, kobj.model_copy())
            
            if resp is STOP_CHAIN:
                logger.info(f"Handler chain stopped by {handler.func.__name__}")
                return STOP_CHAIN
            elif resp is None:
                continue
            elif isinstance(resp, KnowledgeObject):
                kobj = resp
                logger.info(f"Internal event modified by {handler.func.__name__}")
            else:
                raise ValueError(f"Handler {handler.func.__name__} returned invalid response '{resp}'")
                    
        return kobj

        
    def handle_kobj(self, kobj: KnowledgeObject, queue: bool = False):
        if queue:
            logger.info(f"Queued internal event for '{kobj.rid}'")
            self.kobj_queue.put(kobj)
            return
        
        logger.info(f"Started handling internal event for '{kobj.rid}'")
        kobj = self.call_handler_chain(HandlerType.RID, kobj)
        if kobj is STOP_CHAIN: return
        
        if kobj.event_type != EventType.FORGET:
            # attempt to retrieve manifest
            if not kobj.manifest:
                logger.info("Manifest not found, attempting to fetch")
                remote_manifest = self.network.fetch_remote_manifest(kobj.rid)
                if not remote_manifest: return
                kobj.manifest = remote_manifest
            
            kobj = self.call_handler_chain(HandlerType.Manifest, kobj)
            if kobj is STOP_CHAIN: return
            
            # attempt to retrieve bundle
            if not kobj.bundle:
                logger.info("Bundle not found, attempting to fetch")
                remote_bundle = self.network.fetch_remote_bundle(kobj.rid)
                if not remote_bundle: return
                # TODO: WARNING MANIFEST MAY BE DIFFERENT
                kobj.manifest = remote_bundle.manifest
                kobj.contents = remote_bundle.contents
                
            kobj = self.call_handler_chain(HandlerType.Bundle, kobj)
            if kobj is STOP_CHAIN: return
            
        if kobj.normalized_event_type in (EventType.UPDATE, EventType.NEW):
            # cache operation
            logger.info(f"Writing '{kobj.rid}' to cache")
            self.cache.write(kobj.bundle)
        elif kobj.normalized_event_type == EventType.FORGET:
            logger.info(f"Deleting '{kobj.rid}' from cache")
            self.cache.delete(kobj.rid)
        elif kobj.normalized_event_type is None:
            logger.info("Internal event's normalized event type was never set, cannot broadcast to network")
            return
        
        if type(kobj.rid) in (KoiNetNode, KoiNetEdge):
            logger.info("Change to node or edge, regenerating network graph")
            self.network.graph.generate()
        
        # kobj = self.call_handler_chain(HandlerType.Cache, kobj)
        # if kobj is STOP_CHAIN: return
        
        kobj = self.call_handler_chain(HandlerType.Network, kobj)
        if kobj is STOP_CHAIN: return
        
        normalized_event = kobj.to_normalized_event()
        
        # push edges to relevant parties in addition to subscribers
        # if type(kobj.rid) == KoiNetEdge:
        #     edge_profile = kobj.bundle.validate_contents(EdgeModel)
        #     if edge_profile.target == self.identity.rid:
        #         logger.info(f"Pushing event to edge source '{edge_profile.source}'")
        #         self.network.push_event_to(normalized_event, edge_profile.source)
        #     elif edge_profile.source == self.identity.rid:
        #         logger.info(f"Pushing event to edge target '{edge_profile.target}'")
        #         self.network.push_event_to(normalized_event, edge_profile.target)
            
        # self.network.push_event(normalized_event, flush=True)
        
        if kobj.network_targets:
            logger.info(f"Broadcasting event to {len(kobj.network_targets)} network target(s)")
        else:
            logger.info("No network targets set")
        for node in kobj.network_targets:
            self.network.push_event_to(normalized_event, node)
        
        self.network.flush_all_webhook_queues()
        
        kobj = self.call_handler_chain(HandlerType.Final, kobj)
        
        while not self.kobj_queue.empty():
            logger.info(f"Dequeued internal event for '{kobj.rid}'")
            kobj = self.kobj_queue.get()
            self.handle_kobj(kobj)
        
    
    def handle_rid(
        self, 
        rid: RID, 
        source: KnowledgeSource = KnowledgeSource.Internal,
        event_type: KnowledgeEventType = None, 
        queue: bool = False
    ):
        logger.info(f"Handling RID '{rid}', event type: {event_type}")
        kobj = KnowledgeObject(
            rid=rid, 
            event_type=event_type,
            event_source=source
        )
        self.handle_kobj(kobj, queue)
    
    def handle_manifest(
        self, 
        manifest: Manifest, 
        source: KnowledgeSource = KnowledgeSource.Internal,
        event_type: KnowledgeEventType = None, 
        queue: bool = False
    ):
        logger.info(f"Handling Manifest '{manifest.rid}', event type: {event_type}")
        kobj = KnowledgeObject(
            rid=manifest.rid, 
            manifest=manifest, 
            event_type=event_type,
            event_source=source
        )
        self.handle_kobj(kobj, queue)
    
    def handle_bundle(
        self, 
        bundle: Bundle, 
        source: KnowledgeSource = KnowledgeSource.Internal,
        event_type: KnowledgeEventType = None, 
        queue: bool = False
    ):
        logger.info(f"Handling Bundle '{bundle.rid}', event type: {event_type}")
        kobj = KnowledgeObject(
            rid=bundle.rid, 
            manifest=bundle.manifest, 
            contents=bundle.contents, 
            event_type=event_type,
            event_source=source
        )
        self.handle_kobj(kobj, queue)
        
    def handle_event(
        self, 
        event: Event, 
        source: KnowledgeSource = KnowledgeSource.Internal,
        queue: bool = False
    ):
        logger.info(f"Handling Event '{event.rid}, event type: {event.event_type}")
        kobj = KnowledgeObject(
            rid=event.rid,
            manifest=event.manifest,
            contents=event.contents,
            event_type=event.event_type,
            event_source=source
        )
        self.handle_kobj(kobj, queue)
