from typing import Callable
from rid_lib.ext import Event, EventType, Bundle, Cache
from ..rid_types import KoiNetEdge, KoiNetNode
from .handlers import EventHandler, StateHandler, HandlerType
from ..network import NetworkInterface


class ProcessorInterface:
    def __init__(self, cache: Cache, network: NetworkInterface):
        self.cache = cache
        self.network = network
        self.allowed_contexts = [
            KoiNetNode.context,
            KoiNetEdge.context
        ]
        self.state_handlers: list[EventHandler] = []
        self.event_handlers: list[EventHandler] = []
    
    def register_handler(
        self,
        contexts: list[str],
        handler_type: HandlerType
    ):
        def decorator(func: Callable):
            print("registering", handler_type, "handler for", contexts)
            if handler_type == HandlerType.STATE:
                self.state_handlers.append(StateHandler(contexts, func))
            elif handler_type == HandlerType.EVENT:
                self.event_handlers.append(EventHandler(contexts, func))
            return func
        return decorator
    
    def handle_event(self, event: Event) -> EventType | None:
        normalized_type = None
        print("handling event:", event.event_type, event.rid)
        if event.rid.context in self.allowed_contexts:        
            if event.event_type in (EventType.NEW, EventType.UPDATE):
                if event.bundle is None:
                    print("bundle not attached")
                    # TODO: retrieve bundle
                
                normalized_type = self.handle_state(event.bundle)
            elif event.event_type == EventType.FORGET:
                print("deleting", event.rid, "from cache")
                self.cache.delete(event.rid)
                self.network.push_event(event, flush=True)
                normalized_type = EventType.FORGET
        else:
            print("ignoring disallowed context")
        
        for handler in self.event_handlers:
            handler.call(event, normalized_type)
        
        return normalized_type
    
    def handle_state(self, bundle: Bundle) -> EventType | None:
        normalized_type = None
        print("handling state:", bundle.manifest.rid)
        if self.cache.exists(bundle.manifest.rid):
            print("RID known to cache")
            prev_bundle = self.cache.read(bundle.manifest.rid)

            if bundle.manifest.sha256_hash == prev_bundle.manifest.sha256_hash:
                print("no change in knowledge, ignoring")
                return None # same knowledge
            if bundle.manifest.timestamp <= prev_bundle.manifest.timestamp:
                print("older manifest, ignoring")
                return None # incoming state is older
            
            print("newer manifest")
            print("writing", bundle.manifest.rid, "to cache")
            self.cache.write(bundle)
            normalized_type = EventType.UPDATE

        else:
            print("RID unknown to cache")
            print("writing", bundle.manifest.rid, "to cache")
            self.cache.write(bundle)
            normalized_type = EventType.NEW
        
        if bundle.manifest.rid.context in (KoiNetNode.context, KoiNetEdge.context):
            self.network.state.generate()
        
        self.network.push_event(
            Event.from_bundle(normalized_type, bundle),
            flush=True
        )
        
        for handler in self.state_handlers:
            handler.call(bundle, normalized_type)
        
        return normalized_type