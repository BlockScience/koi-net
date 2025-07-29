import logging
from typing import Callable
from rid_lib.core import RIDType
from rid_lib.types import KoiNetEdge, KoiNetNode
from rid_lib.ext import Cache
from ..protocol.event import EventType
from ..network.interface import NetworkInterface
from ..network.graph import NetworkGraph
from ..identity import NodeIdentity
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

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .handler_context import HandlerContext

logger = logging.getLogger(__name__)


class KnowledgePipeline:
    handler_context: "HandlerContext"
    cache: Cache
    identity: NodeIdentity
    network: NetworkInterface
    graph: NetworkGraph
    handlers: list[KnowledgeHandler]
    
    def __init__(
        self, 
        handler_context: "HandlerContext",
        cache: Cache, 
        network: NetworkInterface,
        graph: NetworkGraph,
        default_handlers: list[KnowledgeHandler] = []
    ):
        self.handler_context = handler_context
        self.cache = cache
        self.network = network
        self.graph = graph
        self.handlers = default_handlers
    
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
            resp = handler.func(self.handler_context, kobj.model_copy())
            
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
    
    def process(self, kobj: KnowledgeObject) -> None:
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
            # NOTE: this SHOULD just be a cache read (not deref)
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
                    # TODO: fetch from source node (when integrated with secure protocol)
                    manifest = self.network.fetch_remote_manifest(kobj.rid)
                    
                elif kobj.source == KnowledgeSource.Internal:
                    logger.debug("Attempting to read manifest from cache")
                    # NOTE: does this make sense? should a non FORGET event type allow just the RID to be handled? if its in the cache wouldn't it already have been handled 
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
                    # NOTE: does this make sense? should a non FORGET event type allow just the RID to be handled? if its in the cache wouldn't it already have been handled 
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
            self.graph.generate()
        
        kobj = self.call_handler_chain(HandlerType.Network, kobj)
        if kobj is STOP_CHAIN: return
        
        if kobj.network_targets:
            logger.debug(f"Broadcasting event to {len(kobj.network_targets)} network target(s)")
        else:
            logger.debug("No network targets set")
        
        for node in kobj.network_targets:
            self.network.push_event_to(kobj.normalized_event, node)
            self.network.flush_webhook_queue(node)
        
        kobj = self.call_handler_chain(HandlerType.Final, kobj)
