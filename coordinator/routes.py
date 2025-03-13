from fastapi import APIRouter, BackgroundTasks
from .core import node
from koi_net.models import *
from .config import api_prefix


koi_net_router = APIRouter(prefix=api_prefix)

@koi_net_router.post("/events/broadcast")
def broadcast_events(req: EventsPayload, background: BackgroundTasks):
    for event in req.events:
        background.add_task(node.processor.handle_event, event)


@koi_net_router.post("/events/poll")
def poll_events(req: RequestEvents) -> EventsPayload:
    events = node.network.flush_poll_queue(req.rid)
    return EventsPayload(events=events)


@koi_net_router.post("/state/rids")
def retrieve_rids(req: RequestRids) -> RidsPayload:
    rids = [
        rid for rid in node.cache.read_all_rids()
        if (
            not req.contexts 
            or rid.context in req.contexts
        )
    ]
    return RidsPayload(rids=rids)


@koi_net_router.post("/state/manifests")
def retrieve_manifests(req: RequestManifests) -> ManifestsPayload:
    manifests = [
        bundle.manifest for rid in req.rids or node.cache.read_all_rids()
        if (
            not req.contexts 
            or rid.context in req.contexts
        ) and (
            bundle := node.cache.read(rid)
        )
    ]
    return ManifestsPayload(manifests=manifests)


@koi_net_router.post("/state/bundles")
def retrieve_bundles(req: RequestBundles) -> BundlesPayload:    
    bundles = [
        bundle for rid in req.rids
        if (bundle := node.cache.read(rid))
    ]
    return BundlesPayload(bundles=bundles)
