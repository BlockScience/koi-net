from enum import StrEnum
from pydantic import BaseModel
from rid_lib import RID
from rid_lib.ext import Manifest, Bundle


class EventType(StrEnum):
    NEW = "NEW"
    UPDATE = "UPDATE"
    FORGET = "FORGET"

class Event(BaseModel):
    rid: RID
    event_type: EventType
    manifest: Manifest | None = None
    contents: dict | None = None
    
    def __repr__(self):
        return f"<Event '{self.rid}' event type: '{self.event_type}'>"
    
    @classmethod
    def from_bundle(cls, event_type: EventType, bundle: Bundle):
        return cls(
            rid=bundle.manifest.rid,
            event_type=event_type,
            manifest=bundle.manifest,
            contents=bundle.contents
        )
        
    @classmethod
    def from_manifest(cls, event_type: EventType, manifest: Manifest):
        return cls(
            rid=manifest.rid,
            event_type=event_type,
            manifest=manifest
        )
        
    @classmethod
    def from_rid(cls, event_type: EventType, rid: RID):
        return cls(
            rid=rid,
            event_type=event_type
        )
        
    @property
    def bundle(self):
        if self.manifest is not None and self.contents is not None:
            return Bundle(
                manifest=self.manifest,
                contents=self.contents
            )