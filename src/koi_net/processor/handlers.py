from enum import StrEnum
from typing import Callable
from rid_lib.ext import Event, EventType, Bundle

class HandlerType(StrEnum):
    STATE = "STATE"
    EVENT = "EVENT"

class EventHandler:
    def __init__(
        self, 
        contexts: list[str],
        func: Callable[[Event, EventType | None], None]
    ):
        self.contexts = contexts
        self.func = func
    
    def call(self, event: Event, normalized_type: EventType | None):
        if event.rid.context not in self.contexts: return
        self.func(event, normalized_type)
        
class StateHandler:
    def __init__(
        self, 
        contexts: list[str],
        func: Callable[[Bundle, EventType | None], None]
    ):
        self.contexts = contexts
        self.func = func
    
    def call(self, bundle: Bundle, normalized_type: EventType | None):
        if bundle.rid.context not in self.contexts: return
        self.func(bundle, normalized_type)
