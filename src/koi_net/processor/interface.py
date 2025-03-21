import logging
from dataclasses import dataclass
from typing import Callable
from rid_lib.core import RIDType
from rid_lib.ext import Event, EventType, Bundle, Cache
from ..models import NormalizedType, NodeModel, NodeType
from ..rid_types import KoiNetEdge, KoiNetNode
from ..network import NetworkInterface

logger = logging.getLogger(__name__)


@dataclass
class Handler:
    contexts: list[RIDType]
    func: Callable[[Event | Bundle, NormalizedType], None]
    
    def call(self, obj: Event | Bundle, normalized_type: NormalizedType):
        if type(obj.rid) not in self.contexts:
            return
        
        self.func(obj, normalized_type)


class ProcessorInterface:
    def __init__(self, cache: Cache, network: NetworkInterface):
        self.cache = cache
        self.network = network
        self.allowed_types = [
            KoiNetNode,
            KoiNetEdge
        ]
        self.state_handlers: list[Handler] = []
        self.event_handlers: list[Handler] = []
    
    def register_handler(
        self,
        contexts: list[RIDType],
        handler_list: list[Handler]
):
        def decorator(func: Callable):
            handler_list.append(Handler(contexts, func))
            return func
        return decorator
    
    def register_state_handler(self, contexts: list[RIDType]):
        return self.register_handler(contexts, self.state_handlers)
    
    def register_event_handler(self, contexts: list[RIDType]):
        return self.register_handler(contexts, self.event_handlers)
    
    def handle_event(self, event: Event) -> EventType | None:
        normalized_type = None
        logger.info(f"Handling event {event.event_type} {event.rid}")
        if type(event.rid) in self.allowed_types:        
            if event.event_type in (EventType.NEW, EventType.UPDATE):
                if event.bundle is None:
                    logger.info("Bundle not attached")                    
                    remote_bundle = None
                    for node_rid in self.cache.list_rids(allowed_types=[KoiNetNode]):
                        node_bundle = self.cache.read(node_rid)
                        node = node_bundle.validate_contents(NodeModel)
                        if node.node_type == NodeType.FULL and type(event.rid) in node.provides.state:
                            logger.info(f"Attempting to fetch from {node_rid}")
                            
                            payload = self.network.adapter.fetch_bundles(
                                node=node_rid, rids=[event.rid])
                            
                            if payload.bundles:
                                remote_bundle = payload.bundles[0]
                                logger.info("Got bundle!")
                                break
                
                    bundle = remote_bundle
                else:
                    bundle = event.bundle
                    
                if bundle:
                    normalized_type = self.handle_state(bundle)
                else:
                    normalized_type = None
                    logger.warning("Failed to locate bundle")
                
            elif event.event_type == EventType.FORGET:
                logger.info(f"Deleting {event.rid} from cache")
                self.cache.delete(event.rid)
                self.network.push_event(event, flush=True)
                normalized_type = EventType.FORGET
        else:
            logger.info(f"Ignoring disallowed type {event.event_type}")
        
        for handler in self.event_handlers:
            handler.call(event, normalized_type)
        
        return normalized_type
    
    def handle_state(self, bundle: Bundle) -> EventType | None:
        normalized_type = None
        logger.info(f"Handling state {bundle.manifest.rid}")
        if self.cache.exists(bundle.manifest.rid):
            logger.info("RID known to cache")
            prev_bundle = self.cache.read(bundle.manifest.rid)

            if bundle.manifest.sha256_hash == prev_bundle.manifest.sha256_hash:
                logger.info("No change in knowledge, ignoring")
                return None # same knowledge
            if bundle.manifest.timestamp <= prev_bundle.manifest.timestamp:
                logger.info("Older manifest, ignoring")
                return None # incoming state is older
            
            logger.info(f"Newer manifest, writing {bundle.manifest.rid} to cache")
            self.cache.write(bundle)
            normalized_type = EventType.UPDATE

        else:
            logger.info(f"RID unknown to cache, writing {bundle.manifest.rid} to cache")
            self.cache.write(bundle)
            normalized_type = EventType.NEW
        
        if bundle.manifest.rid.context in (KoiNetNode.context, KoiNetEdge.context):
            self.network.graph.generate()
        
        self.network.push_event(
            Event.from_bundle(normalized_type, bundle),
            flush=True
        )
        
        for handler in self.state_handlers:
            logger.info("Triggering handler")
            handler.call(bundle, normalized_type)
        
        return normalized_type