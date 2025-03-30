import logging
from queue import Queue
from typing import Callable
from rid_lib.core import RID, RIDType
from rid_lib.ext import Bundle, Cache, Manifest
from rid_lib.types.koi_net_edge import KoiNetEdge
from rid_lib.types.koi_net_node import KoiNetNode
from ..identity import NodeIdentity
from ..network import NetworkInterface
from ..protocol.event import Event, EventType
from .handler import (
    KnowledgeHandler, 
    HandlerType, 
    STOP_CHAIN
)
from .knowledge_object import (
    KnowledgeObject,
    KnowledgeSource, 
    KnowledgeEventType
)

logger = logging.getLogger(__name__)


class ProcessorInterface:
    cache: Cache
    network: NetworkInterface
    identity: NodeIdentity
    handlers: list[KnowledgeHandler]
    kobj_queue: Queue[KnowledgeObject]
    
    def __init__(
        self, 
        cache: Cache, 
        network: NetworkInterface,
        identity: NodeIdentity,
        default_handlers: list[KnowledgeHandler] = []
    ):
        self.cache = cache
        self.network = network
        self.identity = identity
        self.handlers: list[KnowledgeHandler] = default_handlers
        self.kobj_queue = Queue()
    
    @classmethod
    def as_handler(
        cls,
        handler_type: HandlerType,
        rid_types: list[RIDType] | None = None
    ):
        """Special decorator that returns a Handler instead of a function."""
        def decorator(func: Callable) -> KnowledgeHandler:
            handler = KnowledgeHandler(func, handler_type, rid_types, )
            return handler
        return decorator
            
    def register_handler(
        self,
        handler_type: HandlerType,
        rid_types: list[RIDType] | None = None
    ):
        """Assigns decorated function as handler for this Processor."""
        def decorator(func: Callable) -> Callable:
            handler = KnowledgeHandler(func, handler_type, rid_types)
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
            
            # stops handler chain execution
            if resp is STOP_CHAIN:
                logger.info(f"Handler chain stopped by {handler.func.__name__}")
                return STOP_CHAIN
            # kobj unmodified
            elif resp is None:
                continue
            # kobj modified by handler
            elif isinstance(resp, KnowledgeObject):
                kobj = resp
                logger.info(f"Knowledge object modified by {handler.func.__name__}")
            else:
                raise ValueError(f"Handler {handler.func.__name__} returned invalid response '{resp}'")
                    
        return kobj

        
    def handle_kobj(self, kobj: KnowledgeObject):
        logger.info(f"Handling {kobj!r}")
        kobj = self.call_handler_chain(HandlerType.RID, kobj)
        if kobj is STOP_CHAIN: return
        
        if kobj.event_type == EventType.FORGET:
            bundle = self.cache.read(kobj.rid)
            if not bundle: 
                logger.info("Local bundle not found")
                return
            
            # the bundle (to be deleted) attached to kobj for downstream analysis
            logger.info("Adding local bundle (to be deleted) to knowledge object")
            kobj.manifest = bundle.manifest
            kobj.contents = bundle.contents
            
        else:
            # attempt to retrieve manifest
            if not kobj.manifest:
                if kobj.source == KnowledgeSource.External:
                    logger.info("Manifest not found, attempting to fetch remotely")
                    manifest = self.network.fetch_remote_manifest(kobj.rid)
                    if not manifest: return
                    
                elif kobj.source == KnowledgeSource.Internal:
                    logger.info("Manifest not found, attempting to read cache")
                    bundle = self.cache.read(kobj.rid)
                    if not bundle: return
                    manifest = bundle.manifest
                
                kobj.manifest = manifest
                
            kobj = self.call_handler_chain(HandlerType.Manifest, kobj)
            if kobj is STOP_CHAIN: return
            
            # attempt to retrieve bundle
            if not kobj.bundle:
                if kobj.source == KnowledgeSource.External:
                    logger.info("Bundle not found, attempting to fetch")
                    bundle = self.network.fetch_remote_bundle(kobj.rid)
                    # TODO: WARNING MANIFEST MAY BE DIFFERENT
                    
                elif kobj.source == KnowledgeSource.Internal:
                    logger.info("Bundle not found, attempting to read cache")
                    bundle = self.cache.read(kobj.rid)
                
                if kobj.manifest != bundle.manifest:
                    logger.warning("Retrieved bundle contains a different manifest")
                
                if not bundle: return
                kobj.manifest = bundle.manifest
                kobj.contents = bundle.contents                
                
            kobj = self.call_handler_chain(HandlerType.Bundle, kobj)
            if kobj is STOP_CHAIN: return
            
        if kobj.normalized_event_type in (EventType.UPDATE, EventType.NEW):
            logger.info(f"Writing {kobj!r} to cache")
            self.cache.write(kobj.bundle)
            
        elif kobj.normalized_event_type == EventType.FORGET:
            logger.info(f"Deleting {kobj!r} from cache")
            self.cache.delete(kobj.rid)
            
        else:
            logger.info("Normalized event type was never set, no cache or network operations will occur")
            return
        
        if type(kobj.rid) in (KoiNetNode, KoiNetEdge):
            logger.info("Change to node or edge, regenerating network graph")
            self.network.graph.generate()
        
        kobj = self.call_handler_chain(HandlerType.Network, kobj)
        if kobj is STOP_CHAIN: return
        
        if kobj.network_targets:
            logger.info(f"Broadcasting event to {len(kobj.network_targets)} network target(s)")
        else:
            logger.info("No network targets set")
        
        for node in kobj.network_targets:
            self.network.push_event_to(kobj.normalized_event, node)
        self.network.flush_all_webhook_queues()
        
        kobj = self.call_handler_chain(HandlerType.Final, kobj)
            
    def queue_kobj(self, kobj: KnowledgeObject, flush: bool = False):
        self.kobj_queue.put(kobj)
        logger.info(f"Queued {kobj!r}")
        
        if flush:
            self.flush_kobj_queue()
                
    def flush_kobj_queue(self):
        while not self.kobj_queue.empty():
            kobj = self.kobj_queue.get()
            logger.info(f"Dequeued {kobj!r}")
            self.handle_kobj(kobj)
            logger.info("Done handling")
        
    def handle(
        self,
        rid: RID | None = None,
        manifest: Manifest | None = None,
        bundle: Bundle | None = None,
        event: Event | None = None,
        event_type: KnowledgeEventType = None,
        source: KnowledgeSource = KnowledgeSource.Internal,
        flush: bool = False
    ):
        if rid:
            kobj = KnowledgeObject.from_rid(rid, event_type, source)
        elif manifest:
            kobj = KnowledgeObject.from_manifest(manifest, event_type, source)
        elif bundle:
            kobj = KnowledgeObject.from_bundle(bundle, event_type, source)
        elif event:
            kobj = KnowledgeObject.from_event(event, source)
        else:
            raise ValueError("One of 'rid', 'manifest', 'bundle', or 'event' must be provided")
          
        self.queue_kobj(kobj, flush)
