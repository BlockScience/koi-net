from enum import StrEnum
from pydantic import BaseModel
from rid_lib.ext import Event, Bundle, Manifest, EventType
from rid_lib.ext.pydantic_adapter import RIDField, RIDTypeField


class ApiPath(StrEnum):
    BROADCAST_EVENTS = "/events/broadcast"
    POLL_EVENTS      = "/events/poll"
    FETCH_RIDS       = "/rids/fetch"
    FETCH_MANIFESTS  = "/manifests/fetch"
    FETCH_BUNDLES    = "/bundles/fetch"


# request models
class PollEvents(BaseModel):
    rid: RIDField
    limit: int = 0
    
class FetchRids(BaseModel):
    allowed_types: list[RIDTypeField] = []
    
class FetchManifests(BaseModel):
    allowed_types: list[RIDTypeField] = []
    rids: list[str] = []
    
class FetchBundles(BaseModel):
    rids: list[RIDField]
    

# response/payload models
class RidsPayload(BaseModel):
    rids: list[RIDField]

class ManifestsPayload(BaseModel):
    manifests: list[Manifest]
    not_found: list[RIDField] | None = None
    
class BundlesPayload(BaseModel):
    bundles: list[Bundle]
    not_found: list[RIDField] | None = None
    deferred: list[RIDField] | None = None
    
class EventsPayload(BaseModel):
    events: list[Event]


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
    rid_types: list[RIDTypeField]
    status: str

type NormalizedType = EventType | None