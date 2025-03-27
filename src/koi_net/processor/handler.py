from dataclasses import dataclass
from enum import StrEnum
from typing import Callable
from rid_lib import RIDType
from rid_lib.ext import Manifest
from ..protocol.event import Event, EventType

# sentinel
STOP_CHAIN = object()

class HandlerType(StrEnum):
    RID = "rid", # guaranteed RID - decides whether to delete from cache OR validate manifest
    Manifest = "manifest", # guaranteed RID, Manifest - decides whether to validate bundle
    Bundle = "bundle", # guaranteed RID, Manifest, contents - decides whether to write to cache
    Cache = "cache"
    Network = "network", # occurs after cache action - decides whether to handle network
    Final = "final" # occurs after network.push - final action


@dataclass
class Handler:
    func: Callable
    handler_type: HandlerType
    rid_types: list[RIDType] | None        
    

type InternalEventType = EventType | None

class InternalEvent(Event):
    event_type: InternalEventType = None
    normalized_event_type: InternalEventType = None      
    
    def update_contents(self, contents: dict):
        self.contents = contents
        self.manifest = Manifest.generate(self.rid, contents)
        
    def to_normalized_event(self):
        if not self.normalized_event_type:
            raise ValueError("Internal event's normalized event type is None, cannot convert to Event")
        
        return Event(
            rid=self.rid,
            event_type=self.normalized_event_type,
            manifest=self.manifest,
            contents=self.contents
        )
  
