"""Pydantic models for request and response/payload objects in the KOI-net API."""

from pydantic import BaseModel
from rid_lib import RID, RIDType
from rid_lib.ext import Bundle, Manifest
from .event import Event
from .errors import ErrorTypes


# REQUEST MODELS

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
    

# RESPONSE/PAYLOAD MODELS

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
    

# ERROR MODELS

class ErrorResponse(BaseModel):
    error: ErrorTypes

# TYPES

type RequestModels = EventsPayload | PollEvents | FetchRids | FetchManifests | FetchBundles
type ResponseModels = RidsPayload | ManifestsPayload | BundlesPayload | EventsPayload | ErrorResponse