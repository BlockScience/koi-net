from enum import StrEnum
from pydantic import BaseModel
from rid_lib import RID
from rid_lib.ext import Manifest
from rid_lib.ext.bundle import Bundle
from rid_lib.types.koi_net_node import KoiNetNode
from ..protocol.event import Event, EventType


type KnowledgeEventType = EventType | None

class KnowledgeSource(StrEnum):
    Internal = "INTERNAL"
    External = "EXTERNAL"

class KnowledgeObject(BaseModel):
    rid: RID
    manifest: Manifest | None = None
    contents: dict | None = None
    event_type: KnowledgeEventType = None
    normalized_event_type: KnowledgeEventType = None
    source: KnowledgeSource
    network_targets: set[KoiNetNode] = set()
    
    @classmethod
    def from_rid(
        cls, 
        rid: RID, 
        event_type: KnowledgeEventType = None, 
        source: KnowledgeSource = KnowledgeSource.Internal
    ) -> "KnowledgeObject":
        return cls(
            rid=rid,
            event_type=event_type,
            source=source
        )
        
    @classmethod
    def from_manifest(
        cls, 
        manifest: Manifest, 
        event_type: KnowledgeEventType = None, 
        source: KnowledgeSource = KnowledgeSource.Internal
    ) -> "KnowledgeObject":
        return cls(
            rid=manifest.rid,
            manifest=manifest,
            event_type=event_type,
            source=source
        )
        
    @classmethod
    def from_bundle(
        cls, 
        bundle: Bundle, 
        event_type: KnowledgeEventType = None, 
        source: KnowledgeSource = KnowledgeSource.Internal
    ) -> "KnowledgeObject":
        return cls(
            rid=bundle.rid,
            manifest=bundle.manifest,
            contents=bundle.contents,
            event_type=event_type,
            source=source
        )
        
    @classmethod
    def from_event(
        cls,
        event: Event,
        source: KnowledgeSource = KnowledgeSource.Internal
    ) -> "KnowledgeObject":
        return cls(
            rid=event.rid,
            manifest=event.manifest,
            contents=event.contents,
            event_type=event.event_type,
            source=source
        )
    
    @property
    def bundle(self):
        if self.manifest is None or self.contents is None:
            return
        
        return Bundle(
            manifest=self.manifest,
            contents=self.contents
        )
    
    @property
    def normalized_event(self):
        if not self.normalized_event_type:
            raise ValueError("Internal event's normalized event type is None, cannot convert to Event")
        
        return Event(
            rid=self.rid,
            event_type=self.normalized_event_type,
            manifest=self.manifest,
            contents=self.contents
        )