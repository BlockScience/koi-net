from enum import StrEnum
from pydantic import BaseModel, RootModel
from rid_lib import RID
from rid_lib.ext import EventType, utils, Bundle, Cache, Event, Manifest
from rid_lib.ext.pydantic_adapter import RIDField

class KoiNetPath(StrEnum):
    HANDSHAKE = "/handshake"
    EVENTS_BROADCAST = "/events/broadcast"
    EVENTS_POLL = "/events/poll"
    STATE_RIDS = "/state/rids"
    STATE_MANIFESTS = "/state/manifests"
    STATE_BUNDLES = "/state/bundles"

class NodeType(StrEnum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"

class Provides(BaseModel):
    event: list[str] = []
    state: list[str] = []

class NodeModel(BaseModel):
    base_url: str | None = None
    node_type: NodeType
    provides: Provides
    
class EdgeModel(BaseModel):
    source: RIDField
    target: RIDField
    comm_type: str
    contexts: list[str]
    status: str

# class NormalizedEventType(StrEnum):
#     NEW = "NEW"
#     UPDATE = "UPDATE"
#     FORGET = "FORGET"
#     IGNORE = "IGNORE"

# class NormalizedEvent(BaseModel):
#     rid: RIDField
#     event_type: NormalizedEventType
#     bundle: Bundle
    
EventArrayModel = RootModel[list[Event]]
class EventQueueModel(BaseModel):
    webhook: dict[RIDField, list[Event]]
    poll: dict[RIDField, list[Event]]
    
BundleArrayModel = RootModel[list[Bundle]]
ManifestArrayModel = RootModel[list[Manifest]]
RIDArrayModel = RootModel[list[RIDField]]
    
def cache_compare(cache: Cache, curr_bundle: Bundle):
    prev_bundle = cache.read(curr_bundle.manifest.rid)
    if prev_bundle is None: 
        return EventType.NEW
    
    curr_contents_hash = utils.sha256_hash_json(curr_bundle.contents) 
    if prev_bundle.manifest.sha256_hash != curr_contents_hash:
        if curr_bundle.manifest.timestamp > prev_bundle.manifest.timestamp:
            return EventType.UPDATE
