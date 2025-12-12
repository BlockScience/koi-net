import structlog
from rid_lib.types import KoiNetEdge, KoiNetNode
from rid_lib.ext import Cache

from ..exceptions import RequestError
from ..protocol.event import EventType
from ..network.request_handler import RequestHandler
from ..network.event_queue import EventQueue
from ..network.graph import NetworkGraph
from ..identity import NodeIdentity
from .handler import (
    KnowledgeHandler,
    HandlerType, 
    STOP_CHAIN,
    StopChain
)
from .knowledge_object import KnowledgeObject
from .context import HandlerContext

log = structlog.stdlib.get_logger()


class KnowledgePipeline:
    handler_context: HandlerContext
    cache: Cache
    identity: NodeIdentity
    request_handler: RequestHandler
    event_queue: EventQueue
    graph: NetworkGraph
    knowledge_handlers: list[KnowledgeHandler]
    
    def __init__(
        self, 
        handler_context: HandlerContext,
        cache: Cache, 
        request_handler: RequestHandler,
        event_queue: EventQueue,
        graph: NetworkGraph,
        knowledge_handlers: list[KnowledgeHandler]
    ):
        self.handler_context = handler_context
        self.cache = cache
        self.request_handler = request_handler
        self.event_queue = event_queue
        self.graph = graph
        self.knowledge_handlers = knowledge_handlers
    
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
        
        for handler in self.knowledge_handlers:
            if handler_type != handler.handler_type: 
                continue
            
            if handler.rid_types and type(kobj.rid) not in handler.rid_types:
                continue
            
            if handler.event_types and kobj.event_type not in handler.event_types:
                continue
            
            log.debug(f"Calling {handler_type} handler '{handler.func.__name__}'")
            
            resp = handler(
                ctx=self.handler_context,
                kobj=kobj.model_copy()
            )
            
            # stops handler chain execution
            if resp is STOP_CHAIN:
                log.debug(f"Handler chain stopped by {handler.func.__name__}")
                return STOP_CHAIN
            
            # kobj unmodified
            elif resp is None:
                continue
            
            # kobj modified by handler
            elif isinstance(resp, KnowledgeObject):
                kobj = resp
                log.debug(f"Knowledge object modified by {handler.func.__name__}")
            
            else:
                raise ValueError(f"Handler {handler.func.__name__} returned invalid response '{resp}'")
            
        return kobj
    
    def process(self, kobj: KnowledgeObject):
        """Sends knowledge object through knowledge processing pipeline.
        
        Handler chains are called in between major events in the 
        pipeline, indicated by their handler type. Each handler type is 
        guaranteed to have access to certain knowledge, and may affect a 
        subsequent action in the pipeline. The five handler types are as 
        follows:
        - RID - provided RID; if event type is `FORGET`, this handler 
        decides whether to delete the knowledge from the cache by 
        setting the normalized event type to `FORGET`, otherwise this 
        handler decides whether to validate the manifest (and fetch it 
        if not provided). After processing, if event type is `FORGET`, 
        the manifest and contents will be retrieved from the local cache, 
        and indicate the last state of the knowledge before it was 
        deleted.
        - Manifest - provided RID, manifest; decides whether to validate 
        the bundle (and fetch it if not provided).
        - Bundle - provided RID, manifest, contents (bundle); decides 
        whether to write knowledge to the cache by setting the 
        normalized event type to `NEW` or `UPDATE`.
        - Network - provided RID, manifest, contents (bundle); decides 
        which nodes (if any) to broadcast an event about this knowledge 
        to.
        - Final - provided RID, manifests, contents (bundle); final 
        action taken after network broadcast.
        
        The pipeline may be stopped by any point by a single handler 
        returning the `STOP_CHAIN` sentinel. In that case, the process 
        will exit immediately. Further handlers of that type and later 
        handler chains will not be called.
        """
        
        log.debug(f"Handling {kobj!r}")
        kobj = self.call_handler_chain(HandlerType.RID, kobj)
        if kobj is STOP_CHAIN: return
        
        if kobj.event_type == EventType.FORGET:
            bundle = self.cache.read(kobj.rid)
            if not bundle:
                log.debug("Local bundle not found")
                return
            
            # the bundle (to be deleted) attached to kobj for downstream analysis
            log.debug("Adding local bundle (to be deleted) to knowledge object")
            kobj.manifest = bundle.manifest
            kobj.contents = bundle.contents
            
        else:
            # attempt to retrieve manifest
            if not kobj.manifest:
                log.debug("Manifest not found")
                if not kobj.source:
                    return
            
                log.debug("Attempting to fetch remote manifest from source")
                try:
                    payload = self.request_handler.fetch_manifests(
                        node=kobj.source,
                        rids=[kobj.rid])
                except RequestError:
                    log.debug("Failed to find manifest")
                    return
                
                kobj.manifest = payload.manifests[0]
                
            kobj = self.call_handler_chain(HandlerType.Manifest, kobj)
            if kobj is STOP_CHAIN: return
            
            # attempt to retrieve bundle
            if not kobj.contents:
                log.debug("Bundle not found")
                if kobj.source is None:
                    return
                
                log.debug("Attempting to fetch remote bundle from source")
                try:
                    payload = self.request_handler.fetch_bundles(
                        node=kobj.source,
                        rids=[kobj.rid]
                    )
                except RequestError:
                    log.debug("Failed to find bundle")
                    return
                
                bundle = payload.bundles[0]
                
                if kobj.manifest != bundle.manifest:
                    log.warning("Retrieved bundle contains a different manifest")
                
                kobj.manifest = bundle.manifest
                kobj.contents = bundle.contents
                
        kobj = self.call_handler_chain(HandlerType.Bundle, kobj)
        if kobj is STOP_CHAIN: return
            
        if kobj.normalized_event_type in (EventType.UPDATE, EventType.NEW):
            log.info(f"Writing to cache: {kobj!r}")
            self.cache.write(kobj.bundle)
            
        elif kobj.normalized_event_type == EventType.FORGET:
            log.info(f"Deleting from cache: {kobj!r}")
            self.cache.delete(kobj.rid)
            
        else:
            log.debug("Normalized event type was not set, no cache or network operations will occur")
            return
        
        if type(kobj.rid) in (KoiNetNode, KoiNetEdge):
            log.debug("Change to node or edge, regenerating network graph")
            self.graph.generate()
        
        kobj = self.call_handler_chain(HandlerType.Network, kobj)
        if kobj is STOP_CHAIN: return
        
        if kobj.network_targets:
            log.debug(f"Broadcasting event to {len(kobj.network_targets)} network target(s)")
        else:
            log.debug("No network targets set")
        
        for node in kobj.network_targets:
            self.event_queue.push(kobj.normalized_event, node)
        
        kobj = self.call_handler_chain(HandlerType.Final, kobj)
