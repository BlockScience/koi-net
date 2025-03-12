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
class PollEventsReq(BaseModel):
    rid: RIDField
    limit: int = 0
    
class RetrieveRidsReq(BaseModel):
    contexts: list[str] = []
    
class RetrieveManifestsReq(BaseModel):
    contexts: list[str] = []
    rids: list[str] = []
    
class RetrieveBundlesReq(BaseModel):
    rids: list[RIDField]
    

# response models
class RetrieveEventsResp(BaseModel):
    events: list[Event]
    
class RetrieveBundlesResp(BaseModel):
    bundles: list[Bundle]

class RetrieveManifestsResp(BaseModel):
    manifests: list[Manifest]

class RetrieveRidsResp(BaseModel):
    rids: list[RIDField]