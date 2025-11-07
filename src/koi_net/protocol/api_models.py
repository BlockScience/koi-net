"""Pydantic models for request and response objects in the KOI-net API."""

from typing import Annotated, Literal
from pydantic import BaseModel, Field
from rid_lib import RID, RIDType
from rid_lib.ext import Bundle, Manifest
from .event import Event
from .errors import ErrorType


# REQUEST MODELS

class PollEvents(BaseModel):
    type: Literal["poll_events"] = Field("poll_events")
    limit: int = 0
    
class FetchRids(BaseModel):
    type: Literal["fetch_rids"] = Field("fetch_rids")
    rid_types: list[RIDType] = []
    
class FetchManifests(BaseModel):
    type: Literal["fetch_manifests"] = Field("fetch_manifests")
    rid_types: list[RIDType] = []
    rids: list[RID] = []
    
class FetchBundles(BaseModel):
    type: Literal["fetch_bundles"] = Field("fetch_bundles")
    rids: list[RID]
    

# RESPONSE/PAYLOAD MODELS

class RidsPayload(BaseModel):
    type: Literal["rids_payload"] = Field("rids_payload")
    rids: list[RID]

class ManifestsPayload(BaseModel):
    type: Literal["manifests_payload"] = Field("manifests_payload")
    manifests: list[Manifest]
    not_found: list[RID] = []
    
class BundlesPayload(BaseModel):
    type: Literal["bundles_payload"] = Field("bundles_payload")
    bundles: list[Bundle]
    not_found: list[RID] = []
    deferred: list[RID] = []
    
class EventsPayload(BaseModel):
    type: Literal["events_payload"] = Field("events_payload")
    events: list[Event]
    

# ERROR MODELS

class ErrorResponse(BaseModel):
    type: Literal["error_response"] = Field("error_response")
    error: ErrorType

# TYPES

type RequestModels = EventsPayload | PollEvents | FetchRids | FetchManifests | FetchBundles
type ResponseModels = RidsPayload | ManifestsPayload | BundlesPayload | EventsPayload | ErrorResponse
type ApiModels = Annotated[
    RequestModels | ResponseModels,
    Field(discriminator="type")
]