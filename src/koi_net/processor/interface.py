from dataclasses import dataclass
import logging
from itertools import chain
from typing import Callable, Literal, TypedDict, Unpack
from rid_lib.core import RIDType
from rid_lib.ext import Event, EventType, Bundle, Cache
from rid_lib.types import KoiNetEdge, KoiNetNode
from ..models import NormalizedType, NodeModel, NodeType
from ..network import NetworkInterface

logger = logging.getLogger(__name__)


type HandlerType = Literal["state", "event"]
type HandlerTarget = Literal["decider", "after-cache", "after-network"]

@dataclass
class Handler:
    func: Callable[["ProcessorInterface", Event | Bundle, NormalizedType], NormalizedType]
    handler_type: HandlerType
    target: HandlerTarget
    rid_types: list[RIDType] | None



class ProcessorInterface:
    default_handlers: list[Handler] = []
    
    def __init__(
        self, 
        cache: Cache, 
        network: NetworkInterface
    ):
        self.cache = cache
        self.network = network
        self.handlers: list[Handler] = []
    
    @classmethod
    def register_default_handler(
        cls,
        handler_type: HandlerType,
        target: HandlerTarget,
        rid_types: list[RIDType] | None = None
    ):
        def decorator(func: Callable):
            handler = Handler(func, handler_type, target, rid_types, )
            cls.default_handlers.append(handler)
            return func
        return decorator
            
    def register_handler(
        self,
        handler_type: HandlerType,
        target: HandlerTarget,
        rid_types: list[RIDType] | None = None
    ):
        def decorator(func: Callable):
            handler = Handler(func, handler_type, target, rid_types)
            self.handlers.append(handler)
            return func
        return decorator
            
    def call_handlers(
        self, 
        obj: Event | Bundle, 
        normalized_type: NormalizedType,
        handler_type: HandlerType,
        target: HandlerTarget
    ):
        combined_handlers = chain(
            reversed(self.handlers),
            reversed(self.default_handlers)
        )
        
        for handler in combined_handlers:
            print(handler)
            if handler_type != handler.handler_type: 
                continue
            if target != handler.target: 
                continue
            if (handler.rid_types is not None and type(obj.rid) not in handler.rid_types): 
                continue
            
            logger.info(f"Triggered handler: {handler.func.__name__}")
            result = handler.func(self, obj, normalized_type)
            
            if target == "decider":
                return result
    
    def handle_event(self, event: Event) -> NormalizedType:
        normalized_type = None
        logger.info(f"Handling event {event.event_type} {event.rid}")
        
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
        
        self.call_handlers(event, normalized_type, "before-network")
        
        return normalized_type
    
    def handle_state(self, bundle: Bundle) -> NormalizedType:
        logger.info(f"Handling state {bundle.manifest.rid}")
        
        normalized_type = self.call_handlers(bundle, None, "state", "decider")
        if normalized_type is None: return
        
        self.call_handlers(bundle, normalized_type, "state", "after-cache")
        
        self.network.push_event(
            Event.from_bundle(normalized_type, bundle),
            flush=True
        )
        
        self.call_handlers(bundle, normalized_type, "state", "after-network")

        
        return normalized_type