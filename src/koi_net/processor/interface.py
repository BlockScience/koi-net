import logging
from dataclasses import dataclass
from typing import Callable, Literal
from rid_lib.core import RIDType
from rid_lib.ext import Bundle, Cache
from ..network import NetworkInterface
from ..protocol.event import Event, EventType

logger = logging.getLogger(__name__)

type NormalizedType = EventType | None

type HandlerType = Literal["state", "event"]
type HandlerOrder = Literal["decider", "after-cache", "after-network"]
type HandlerFunc = Callable[["ProcessorInterface", Event | Bundle, NormalizedType], NormalizedType]

@dataclass
class Handler:
    func: HandlerFunc
    handler_type: HandlerType
    order: HandlerOrder
    rid_types: list[RIDType] | None


class ProcessorInterface:    
    def __init__(
        self, 
        cache: Cache, 
        network: NetworkInterface,
        default_handlers: list[Handler] = []
    ):
        self.cache = cache
        self.network = network
        self.handlers: list[Handler] = default_handlers
    
    @classmethod
    def as_handler(
        cls,
        handler_type: HandlerType,
        order: HandlerOrder,
        rid_types: list[RIDType] | None = None
    ):
        """Special decorator that returns a Handler instead of a function."""
        def decorator(func: HandlerFunc) -> Handler:
            handler = Handler(func, handler_type, order, rid_types, )
            return handler
        return decorator
            
    def register_handler(
        self,
        handler_type: HandlerType,
        order: HandlerOrder,
        rid_types: list[RIDType] | None = None
    ):
        """Assigns decorated function as handler for this Processor."""
        def decorator(func: HandlerFunc) -> HandlerFunc:
            handler = Handler(func, handler_type, order, rid_types)
            self.handlers.append(handler)
            return func
        return decorator
            
    def call_handlers(
        self, 
        obj: Event | Bundle, 
        normalized_type: NormalizedType,
        handler_type: HandlerType,
        order: HandlerOrder
    ):
        valid_handlers: list[Handler] = []
        for handler in reversed(self.handlers):
            print(handler)
            if handler_type != handler.handler_type: 
                continue
            if order != handler.order: 
                continue
            if (handler.rid_types is not None and type(obj.rid) not in handler.rid_types): 
                continue
            
            valid_handlers.append(handler)
            
        if order == "decider" and len(valid_handlers) > 1:
            logger.warning(f"More than one 'decider' handler was valid, only {valid_handlers[0].func.__name__} will be triggered")
            
        for handler in valid_handlers:
            logger.info(f"Triggered handler: {handler.func.__name__}")
            
            result = handler.func(self, obj, normalized_type)
            
            if order == "decider":
                return result
    
    def handle_event(self, event: Event) -> NormalizedType:
        normalized_type = None
        logger.info(f"Handling event {event.event_type} {event.rid}")
        
        # decider
        
        if event.event_type in (EventType.NEW, EventType.UPDATE):
            bundle = event.bundle or self.network.fetch_remote_bundle(event.rid)
            
            if bundle:
                normalized_type = self.handle_state(bundle)
            else:
                logger.warning("Failed to locate bundle")
                
            
        elif event.event_type == EventType.FORGET:
            logger.info(f"Deleting {event.rid} from cache")
            self.cache.delete(event.rid)
            self.network.push_event(event, flush=True)
            normalized_type = EventType.FORGET
            
        else:
            raise ValueError(f"Unexpected event type: {event.event_type}")
        
        # after-state
        
        # self.call_handlers(event, normalized_type, "before-network")
        
        return normalized_type
    
    def handle_state(self, bundle: Bundle) -> NormalizedType:
        logger.info(f"Handling state {bundle.manifest.rid}")
        
        normalized_type = self.call_handlers(bundle, None, "state", "decider")
        
        if normalized_type in (EventType.NEW, EventType.UPDATE):
            self.cache.write(bundle)
        elif normalized_type == EventType.FORGET:
            self.cache.delete(bundle)
        else:
            return
        
        self.call_handlers(bundle, normalized_type, "state", "after-cache")
        
        self.network.push_event(
            Event.from_bundle(normalized_type, bundle),
            flush=True
        )
        
        self.call_handlers(bundle, normalized_type, "state", "after-network")

        
        return normalized_type