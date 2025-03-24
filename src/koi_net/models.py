from enum import StrEnum
from pydantic import BaseModel
from rid_lib import RID, RIDType
from rid_lib.ext import Event, Bundle, Manifest, EventType
from rid_lib.types import KoiNetNode, KoiNetEdge


class ApiPath(StrEnum):
    BROADCAST_EVENTS = "/events/broadcast"
    POLL_EVENTS      = "/events/poll"
    FETCH_RIDS       = "/rids/fetch"
    FETCH_MANIFESTS  = "/manifests/fetch"
    FETCH_BUNDLES    = "/bundles/fetch"


# request models
class PollEvents(BaseModel):
    rid: RID
    limit: int = 0
    
class FetchRids(BaseModel):
    rid_types: list[RIDType] = []
    
class FetchManifests(BaseModel):
    rid_types: list[RIDType] = []
    rids: list[RID] = []
    
class FetchBundles(BaseModel):
    rids: list[RID]
    

# response/payload models
class RidsPayload(BaseModel):
    rids: list[RID]

class ManifestsPayload(BaseModel):
    manifests: list[Manifest]
    not_found: list[RID] = []
    
class BundlesPayload(BaseModel):
    bundles: list[Bundle]
    not_found: list[RID] = []
    deferred: list[RID] = []
    
class EventsPayload(BaseModel):
    events: list[Event]


# koi-net models
class NodeType(StrEnum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"

class Provides(BaseModel):
    event: list[RIDType] = []
    state: list[RIDType] = []

class NodeModel(BaseModel):
    base_url: str | None = None
    node_type: NodeType
    provides: Provides
    
class EdgeModel(BaseModel):
    source: KoiNetNode
    target: KoiNetNode
    comm_type: str
    rid_types: list[RIDType]
    status: str

type NormalizedType = EventType | None