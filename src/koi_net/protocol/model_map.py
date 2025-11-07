from typing import NamedTuple
from pydantic import BaseModel
from .envelope import SignedEnvelope
from .consts import (
    BROADCAST_EVENTS_PATH, 
    POLL_EVENTS_PATH,
    FETCH_BUNDLES_PATH, 
    FETCH_MANIFESTS_PATH, 
    FETCH_RIDS_PATH
)
from .api_models import (
    EventsPayload,
    PollEvents,
    FetchBundles,
    BundlesPayload,
    FetchManifests,
    ManifestsPayload,
    FetchRids,
    RidsPayload
)


class Models(NamedTuple):
    request: type[BaseModel]
    response: type[BaseModel] | None
    request_envelope: type[SignedEnvelope]
    response_envelope: type[SignedEnvelope] | None


API_MODEL_MAP: dict[str, Models] = {
    BROADCAST_EVENTS_PATH: Models(
        request=EventsPayload,
        response=None,
        request_envelope=SignedEnvelope[EventsPayload],
        response_envelope=None
    ),
    POLL_EVENTS_PATH: Models(
        request=PollEvents,
        response=EventsPayload,
        request_envelope=SignedEnvelope[PollEvents],
        response_envelope=SignedEnvelope[EventsPayload]
    ),
    FETCH_BUNDLES_PATH: Models(
        request=FetchBundles,
        response=BundlesPayload,
        request_envelope=SignedEnvelope[FetchBundles],
        response_envelope=SignedEnvelope[BundlesPayload]
    ),
    FETCH_MANIFESTS_PATH: Models(
        request=FetchManifests,
        response=ManifestsPayload,
        request_envelope=SignedEnvelope[FetchManifests],
        response_envelope=SignedEnvelope[ManifestsPayload]
    ),
    FETCH_RIDS_PATH: Models(
        request=FetchRids,
        response=RidsPayload,
        request_envelope=SignedEnvelope[FetchRids],
        response_envelope=SignedEnvelope[RidsPayload]
    )
}