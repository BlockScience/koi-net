import logging
from queue import Queue
from typing import Callable
from rid_lib.core import RID, RIDType
from rid_lib.ext import Bundle, Cache, Manifest
from rid_lib.types.koi_net_edge import KoiNetEdge
from rid_lib.types.koi_net_node import KoiNetNode
from koi_net.identity import NodeIdentity
from koi_net.protocol.edge import EdgeModel
from ..network import NetworkInterface
from ..protocol.event import Event, EventType
from .handler import (
    Handler, 
    HandlerType, 
    InternalEvent, 
    InternalEventType,
    STOP_CHAIN
)

logger = logging.getLogger(__name__)


class ProcessorInterface:
    cache: Cache
    network: NetworkInterface
    identity: NodeIdentity
    handlers: list[Handler]
    ievent_queue: Queue[InternalEvent]
    
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
        self.ievent_queue = Queue()
    
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
        ievent: InternalEvent
    ):
        for handler in self.handlers:
            if handler_type != handler.handler_type: 
                continue
            
            if handler.rid_types and type(ievent.rid) not in handler.rid_types:
                continue
            
            logger.info(f"Calling {handler_type} handler '{handler.func.__name__}'")
            resp = handler.func(self, ievent.model_copy())
            
            if resp is STOP_CHAIN:
                logger.info(f"Handler chain stopped by {handler.func.__name__}")
                return STOP_CHAIN
            elif resp is None:
                continue
            elif isinstance(resp, InternalEvent):
                ievent = resp
                logger.info(f"Internal event modified by {handler.func.__name__}")
            else:
                raise ValueError(f"Handler {handler.func.__name__} returned invalid response '{resp}'")
                    
        return ievent

        
    def handle_ievent(self, ievent: InternalEvent, queue: bool = False):
        if queue:
            logger.info(f"Queued internal event for '{ievent.rid}'")
            self.ievent_queue.put(ievent)
            return
        
        logger.info(f"Started handling internal event for '{ievent.rid}'")
        ievent = self.call_handler_chain(HandlerType.RID, ievent)
        if ievent is STOP_CHAIN: return
        
        if ievent.event_type != EventType.FORGET:
            # attempt to retrieve manifest
            if not ievent.manifest:
                logger.info("Manifest not found, attempting to fetch")
                remote_manifest = self.network.fetch_remote_manifest(ievent.rid)
                if not remote_manifest: return
                ievent.manifest = remote_manifest
            
            ievent = self.call_handler_chain(HandlerType.Manifest, ievent)
            if ievent is STOP_CHAIN: return
            
            # attempt to retrieve bundle
            if not ievent.bundle:
                logger.info("Bundle not found, attempting to fetch")
                remote_bundle = self.network.fetch_remote_bundle(ievent.rid)
                if not remote_bundle: return
                # TODO: WARNING MANIFEST MAY BE DIFFERENT
                ievent.manifest = remote_bundle.manifest
                ievent.contents = remote_bundle.contents
                
            ievent = self.call_handler_chain(HandlerType.Bundle, ievent)
            if ievent is STOP_CHAIN: return
            
        if ievent.normalized_event_type in (EventType.UPDATE, EventType.NEW):
            # cache operation
            logger.info(f"Writing '{ievent.rid}' to cache")
            self.cache.write(ievent.bundle)
        elif ievent.normalized_event_type == EventType.FORGET:
            logger.info(f"Deleting '{ievent.rid}' from cache")
            self.cache.delete(ievent.rid)
        elif ievent.normalized_event_type is None:
            logger.info("Internal event's normalized event type was never set, cannot broadcast to network")
            return
        
        if type(ievent.rid) in (KoiNetNode, KoiNetEdge):
            logger.info("Change to node or edge, regenerating network graph")
            self.network.graph.generate()
        
        ievent = self.call_handler_chain(HandlerType.Cache, ievent)
        if ievent is STOP_CHAIN: return
        
        ievent = self.call_handler_chain(HandlerType.Network, ievent)
        if ievent is STOP_CHAIN: return

        logger.info(f"Pushing event {ievent.normalized_event_type} '{ievent.rid}' to network")
        
        normalized_event = ievent.to_normalized_event()
        
        # push edges to relevant parties in addition to subscribers
        if type(ievent.rid) == KoiNetEdge:
            edge_profile = ievent.bundle.validate_contents(EdgeModel)
            if edge_profile.target == self.identity.rid:
                logger.info(f"Pushing event to edge source '{edge_profile.source}'")
                self.network.push_event_to(normalized_event, edge_profile.source)
            elif edge_profile.source == self.identity.rid:
                logger.info(f"Pushing event to edge target '{edge_profile.target}'")
                self.network.push_event_to(normalized_event, edge_profile.target)
            
        self.network.push_event(normalized_event, flush=True)
        
        ievent = self.call_handler_chain(HandlerType.Final, ievent)
        
        while not self.ievent_queue.empty():
            logger.info(f"Dequeued internal event for '{ievent.rid}'")
            ievent = self.ievent_queue.get()
            self.handle_ievent(ievent)
        
    
    def handle_rid(self, rid: RID, event_type: InternalEventType = None, queue: bool = False):
        logger.info(f"Handling RID '{rid}', event type: {event_type}")
        ievent = InternalEvent(
            rid=rid, 
            event_type=event_type
        )
        self.handle_ievent(ievent, queue)
    
    def handle_manifest(
        self, 
        manifest: Manifest, 
        event_type: InternalEventType = None, 
        queue: bool = False
    ):
        logger.info(f"Handling Manifest '{manifest.rid}', event type: {event_type}")
        ievent = InternalEvent(
            rid=manifest.rid, 
            manifest=manifest, 
            event_type=event_type
        )
        self.handle_ievent(ievent, queue)
    
    def handle_bundle(
        self, 
        bundle: Bundle, 
        event_type: InternalEventType = None, 
        queue: bool = False
    ):
        logger.info(f"Handling Bundle '{bundle.rid}', event type: {event_type}")
        ievent = InternalEvent(
            rid=bundle.rid, 
            manifest=bundle.manifest, 
            contents=bundle.contents, 
            event_type=event_type
        )
        self.handle_ievent(ievent, queue)
        
    def handle_event(self, event: Event, queue: bool = False):
        logger.info(f"Handling Event '{event.rid}, event type: {event.event_type}")
        ievent = InternalEvent(
            rid=event.rid,
            manifest=event.manifest,
            contents=event.contents,
            event_type=event.event_type
        )
        self.handle_ievent(ievent, queue)
