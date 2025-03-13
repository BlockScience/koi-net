from enum import StrEnum
from pydantic import BaseModel, RootModel
from rid_lib.ext import Event, Bundle, Manifest
from rid_lib.ext.pydantic_adapter import RIDField


class KoiNetPath(StrEnum):
    EVENTS_BROADCAST = "/events/broadcast"
    EVENTS_POLL = "/events/poll"
    STATE_RIDS = "/state/rids"
    STATE_MANIFESTS = "/state/manifests"
    STATE_BUNDLES = "/state/bundles"


# request models
class RequestEvents(BaseModel):
    rid: RIDField
    limit: int = 0
    
class RequestRids(BaseModel):
    contexts: list[str] = []
    
class RequestManifests(BaseModel):
    contexts: list[str] = []
    rids: list[str] = []
    
class RequestBundles(BaseModel):
    rids: list[RIDField]
    

# response models
class EventsPayload(BaseModel):
    events: list[Event]
    
class BundlesPayload(BaseModel):
    bundles: list[Bundle]

class ManifestsPayload(BaseModel):
    manifests: list[Manifest]

class RidsPayload(BaseModel):
    rids: list[RIDField]
    

# koi-net models
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

class EventQueueModel(BaseModel):
    webhook: dict[RIDField, list[Event]]
    poll: dict[RIDField, list[Event]]