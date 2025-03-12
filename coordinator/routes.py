from fastapi import APIRouter, BackgroundTasks
from .core import cache, network, processor
from .network.models import *
from .config import api_prefix


koi_net_router = APIRouter(prefix=api_prefix)

@koi_net_router.post("/events/broadcast")
def broadcast_events(req: RetrieveEventsResp, background: BackgroundTasks):
    for event in req.events:
        background.add_task(processor.route_event, event)


@koi_net_router.post("/events/poll")
def poll_events(poll: PollEventsReq) -> RetrieveEventsResp:
    events = network.flush_poll_queue(poll.rid)
    return RetrieveEventsResp(events=events)


@koi_net_router.post("/state/rids")
def retrieve_rids(retrieve: RetrieveRidsReq = RetrieveRidsReq()) -> RetrieveRidsResp:
    rids = [
        rid for rid in cache.read_all_rids()
        if (
            not retrieve.contexts 
            or rid.context in retrieve.contexts
        )
    ]
    return RetrieveRidsResp(rids=rids)


@koi_net_router.post("/state/manifests")
def retrieve_manifests(retrieve: RetrieveManifestsReq = RetrieveManifestsReq()) -> RetrieveManifestsResp:
    manifests = [
        bundle.manifest for rid in retrieve.rids or cache.read_all_rids()
        if (
            not retrieve.contexts 
            or rid.context in retrieve.contexts
        ) and (
            bundle := cache.read(rid)
        )
    ]
    return RetrieveManifestsResp(manifests=manifests)


@koi_net_router.post("/state/bundles")
def retrieve_bundles(retrieve: RetrieveBundlesReq) -> RetrieveBundlesResp:    
    bundles = [
        bundle for rid in retrieve.rids
        if (bundle := cache.read(rid))
    ]
    return RetrieveBundlesResp(bundles=bundles)
