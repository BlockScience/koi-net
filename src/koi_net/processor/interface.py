import logging
import queue
import threading
from typing import Callable, Generic
from rid_lib.core import RID, RIDType
from rid_lib.ext import Bundle, Cache, Manifest
from rid_lib.types.koi_net_edge import KoiNetEdge
from rid_lib.types.koi_net_node import KoiNetNode
from ..identity import NodeIdentity
from ..network import NetworkInterface
from ..protocol.event import Event, EventType
from ..config import Config
from .handler import (
    KnowledgeHandler, 
    HandlerType, 
    STOP_CHAIN,
    StopChain
)
from .knowledge_object import (
    KnowledgeObject,
    KnowledgeSource, 
    KnowledgeEventType
)

logger = logging.getLogger(__name__)


class ProcessorInterface():
    """Provides access to this node's knowledge processing pipeline."""
    
    config: Config
    cache: Cache
    network: NetworkInterface
    identity: NodeIdentity
    handlers: list[KnowledgeHandler]
    kobj_queue: queue.Queue[KnowledgeObject]
    use_kobj_processor_thread: bool
    worker_thread: threading.Thread | None = None
    
    def __init__(
        self,
        config: Config,
        cache: Cache, 
        network: NetworkInterface,
        identity: NodeIdentity,
        use_kobj_processor_thread: bool,
        default_handlers: list[KnowledgeHandler] = []
    ):
        self.config = config
        self.cache = cache
        self.network = network
        self.identity = identity
        self.use_kobj_processor_thread = use_kobj_processor_thread
        self.handlers: list[KnowledgeHandler] = default_handlers
        self.kobj_queue = queue.Queue()
        
        if self.use_kobj_processor_thread:
            self.worker_thread = threading.Thread(
                target=self.kobj_processor_worker,
                daemon=True
            )
        
    def add_handler(self, handler: KnowledgeHandler):
        self.handlers.append(handler)
            
    def register_handler(
        self,
        handler_type: HandlerType,
        rid_types: list[RIDType] | None = None,
        source: KnowledgeSource | None = None,
        event_types: list[KnowledgeEventType] | None = None
    ):
        """Assigns decorated function as handler for this processor."""
        def decorator(func: Callable) -> Callable:
            handler = KnowledgeHandler(func, handler_type, rid_types, source, event_types)
            self.add_handler(handler)
            return func
        return decorator
            
    def call_handler_chain(
        self, 
        handler_type: HandlerType,
        kobj: KnowledgeObject
    ) -> KnowledgeObject | StopChain:
        """Calls handlers of provided type, chaining their inputs and outputs together.
        
        The knowledge object provided when this function is called will be passed to the first handler. A handler may return one of three types: 
        - `KnowledgeObject` - to modify the knowledge object for the next handler in the chain
        - `None` - to keep the same knowledge object for the next handler in the chain
        - `STOP_CHAIN` - to stop the handler chain and immediately exit the processing pipeline
        
        Handlers will only be called in the chain if their handler and RID type match that of the inputted knowledge object. 
        """
        
        for handler in self.handlers:
            if handler_type != handler.handler_type: 
                continue
            
            if handler.rid_types and type(kobj.rid) not in handler.rid_types:
                continue
            
            if handler.source and handler.source != kobj.source:
                continue
            
            if handler.event_types and kobj.event_type not in handler.event_types:
                continue
            
            logger.debug(f"Calling {handler_type} handler '{handler.func.__name__}'")
            resp = handler.func(self, kobj.model_copy())
            
            # stops handler chain execution
            if resp is STOP_CHAIN:
                logger.debug(f"Handler chain stopped by {handler.func.__name__}")
                return STOP_CHAIN
            # kobj unmodified
            elif resp is None:
                continue
            # kobj modified by handler
            elif isinstance(resp, KnowledgeObject):
                kobj = resp
                logger.debug(f"Knowledge object modified by {handler.func.__name__}")
            else:
                raise ValueError(f"Handler {handler.func.__name__} returned invalid response '{resp}'")
                    
        return kobj

        
    def process_kobj(self, kobj: KnowledgeObject) -> None:
        """Sends provided knowledge obejct through knowledge processing pipeline.
        
        Handler chains are called in between major events in the pipeline, indicated by their handler type. Each handler type is guaranteed to have access to certain knowledge, and may affect a subsequent action in the pipeline. The five handler types are as follows:
        - RID - provided RID; if event type is `FORGET`, this handler decides whether to delete the knowledge from the cache by setting the normalized event type to `FORGET`, otherwise this handler decides whether to validate the manifest (and fetch it if not provided).
        - Manifest - provided RID, manifest; decides whether to validate the bundle (and fetch it if not provided).
        - Bundle - provided RID, manifest, contents (bundle); decides whether to write knowledge to the cache by setting the normalized event type to `NEW` or `UPDATE`.
        - Network - provided RID, manifest, contents (bundle); decides which nodes (if any) to broadcast an event about this knowledge to. (Note, if event type is `FORGET`, the manifest and contents will be retrieved from the local cache, and indicate the last state of the knowledge before it was deleted.)
        - Final - provided RID, manifests, contents (bundle); final action taken after network broadcast.
        
        The pipeline may be stopped by any point by a single handler returning the `STOP_CHAIN` sentinel. In that case, the process will exit immediately. Further handlers of that type and later handler chains will not be called.
        """
        
        logger.debug(f"Handling {kobj!r}")
        kobj = self.call_handler_chain(HandlerType.RID, kobj)
        if kobj is STOP_CHAIN: return
        
        if kobj.event_type == EventType.FORGET:
            bundle = self.cache.read(kobj.rid)
            if not bundle: 
                logger.debug("Local bundle not found")
                return
            
            # the bundle (to be deleted) attached to kobj for downstream analysis
            logger.debug("Adding local bundle (to be deleted) to knowledge object")
            kobj.manifest = bundle.manifest
            kobj.contents = bundle.contents
            
        else:
            # attempt to retrieve manifest
            if not kobj.manifest:
                logger.debug("Manifest not found")
                if kobj.source == KnowledgeSource.External:
                    logger.debug("Attempting to fetch remote manifest")
                    manifest = self.network.fetch_remote_manifest(kobj.rid)
                    
                elif kobj.source == KnowledgeSource.Internal:
                    logger.debug("Attempting to read manifest from cache")
                    bundle = self.cache.read(kobj.rid)
                    if bundle: 
                        manifest = bundle.manifest
                    else:
                        manifest = None
                        return
                    
                if not manifest:
                    logger.debug("Failed to find manifest")
                    return
                
                kobj.manifest = manifest
                
            kobj = self.call_handler_chain(HandlerType.Manifest, kobj)
            if kobj is STOP_CHAIN: return
            
            # attempt to retrieve bundle
            if not kobj.bundle:
                logger.debug("Bundle not found")
                if kobj.source == KnowledgeSource.External:
                    logger.debug("Attempting to fetch remote bundle")
                    bundle = self.network.fetch_remote_bundle(kobj.rid)
                    
                elif kobj.source == KnowledgeSource.Internal:
                    logger.debug("Attempting to read bundle from cache")
                    bundle = self.cache.read(kobj.rid)
                
                if not bundle: 
                    logger.debug("Failed to find bundle")
                    return
                
                if kobj.manifest != bundle.manifest:
                    logger.warning("Retrieved bundle contains a different manifest")
                
                kobj.manifest = bundle.manifest
                kobj.contents = bundle.contents                
                
        kobj = self.call_handler_chain(HandlerType.Bundle, kobj)
        if kobj is STOP_CHAIN: return
            
        if kobj.normalized_event_type in (EventType.UPDATE, EventType.NEW):
            logger.info(f"Writing to cache: {kobj!r}")
            self.cache.write(kobj.bundle)
            
        elif kobj.normalized_event_type == EventType.FORGET:
            logger.info(f"Deleting from cache: {kobj!r}")
            self.cache.delete(kobj.rid)
            
        else:
            logger.debug("Normalized event type was never set, no cache or network operations will occur")
            return
        
        if type(kobj.rid) in (KoiNetNode, KoiNetEdge):
            logger.debug("Change to node or edge, regenerating network graph")
            self.network.graph.generate()
        
        kobj = self.call_handler_chain(HandlerType.Network, kobj)
        if kobj is STOP_CHAIN: return
        
        if kobj.network_targets:
            logger.debug(f"Broadcasting event to {len(kobj.network_targets)} network target(s)")
        else:
            logger.debug("No network targets set")
        
        for node in kobj.network_targets:
            self.network.push_event_to(kobj.normalized_event, node)
            if not self.network.flush_webhook_queue(node):
                logger.warning("Dropping unresponsive node")
                self.handle(rid=node, event_type=EventType.FORGET)
        
        kobj = self.call_handler_chain(HandlerType.Final, kobj)

    def flush_kobj_queue(self):
        """Flushes all knowledge objects from queue and processes them.
        
        NOTE: ONLY CALL THIS METHOD IN SINGLE THREADED NODES, OTHERWISE THIS WILL CAUSE RACE CONDITIONS.
        """
        if self.use_kobj_processor_thread:
            logger.warning("You are using a worker thread, calling this method can cause race conditions!")
        
        while not self.kobj_queue.empty():
            kobj = self.kobj_queue.get()
            logger.debug(f"Dequeued {kobj!r}")
            
            try:
                self.process_kobj(kobj)
            finally:
                self.kobj_queue.task_done()
            logger.debug("Done")
    
    def kobj_processor_worker(self, timeout=0.1):
        while True:
            try:
                kobj = self.kobj_queue.get(timeout=timeout)
                logger.debug(f"Dequeued {kobj!r}")
                
                try:
                    self.process_kobj(kobj)
                finally:
                    self.kobj_queue.task_done()
                logger.debug("Done")
            
            except queue.Empty:
                pass
            
            except Exception as e:
                logger.warning(f"Error processing kobj: {e}")
        
    def handle(
        self,
        rid: RID | None = None,
        manifest: Manifest | None = None,
        bundle: Bundle | None = None,
        event: Event | None = None,
        kobj: KnowledgeObject | None = None,
        event_type: KnowledgeEventType = None,
        source: KnowledgeSource = KnowledgeSource.Internal
    ):
        """Queues provided knowledge to be handled by processing pipeline.
        
        Knowledge may take the form of an RID, manifest, bundle, event, or knowledge object (with an optional event type for RID, manifest, or bundle objects). All objects will be normalized into knowledge objects and queued. If `flush` is `True`, the queue will be flushed immediately after adding the new knowledge.
        """
        if rid:
            _kobj = KnowledgeObject.from_rid(rid, event_type, source)
        elif manifest:
            _kobj = KnowledgeObject.from_manifest(manifest, event_type, source)
        elif bundle:
            _kobj = KnowledgeObject.from_bundle(bundle, event_type, source)
        elif event:
            _kobj = KnowledgeObject.from_event(event, source)
        elif kobj:
            _kobj = kobj
        else:
            raise ValueError("One of 'rid', 'manifest', 'bundle', 'event', or 'kobj' must be provided")
        
        self.kobj_queue.put(_kobj)
        logger.debug(f"Queued {_kobj!r}")
