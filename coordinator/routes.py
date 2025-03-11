from fastapi import APIRouter, BackgroundTasks
from rid_lib.ext import Bundle, Event
from rid_lib.ext.manifest import Manifest
from rid_lib.ext.pydantic_adapter import RIDField
from .core import cache, network, processor
from .network.models import *
from .config import api_prefix


koi_net_router = APIRouter(prefix=api_prefix)

@koi_net_router.post("/events/broadcast")
def broadcast_events(events: list[Event], background: BackgroundTasks):
    for event in events:
        background.add_task(processor.route_event, event)


@koi_net_router.post("/events/poll")
def poll_events(poll: PollEvents) -> list[Event]:
    events = network.flush_poll_queue(poll.rid)
    return events


@koi_net_router.post("/state/rids")
def retrieve_rids(retrieve: RetrieveRids = RetrieveRids()) -> list[RIDField]:
    return [
        rid for rid in cache.read_all_rids()
        if (
            not retrieve.contexts 
            or rid.context in retrieve.contexts
        )
    ]
    

@koi_net_router.post("/state/manifests")
def retrieve_manifests(retrieve: RetrieveManifests = RetrieveManifests()) -> list[Manifest]:
    return [
        bundle.manifest for rid in retrieve.rids or cache.read_all_rids()
        if (
            not retrieve.contexts 
            or rid.context in retrieve.contexts
        ) and (
            bundle := cache.read(rid)
        )
    ]


@koi_net_router.post("/state/bundles")
def retrieve_bundles(retrieve: RetrieveBundles) -> list[Bundle]:    
    return [
        bundle for rid in retrieve.rids
        if (bundle := cache.read(rid))
    ]
