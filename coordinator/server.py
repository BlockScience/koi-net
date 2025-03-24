import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from rid_lib import RID
from rid_lib.ext import Manifest, Bundle
from koi_net.models import (
    ApiPath,
    PollEvents,
    FetchRids,
    FetchManifests,
    FetchBundles,
    EventsPayload,
    RidsPayload,
    ManifestsPayload,
    BundlesPayload
)
from .core import node
from .config import api_prefix

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):    
    yield
    
    node.network.save_queues()

app = FastAPI(lifespan=lifespan, root_path=api_prefix)

@app.post(ApiPath.BROADCAST_EVENTS)
def broadcast_events(req: EventsPayload, background: BackgroundTasks):
    logger.info(f"Request to {ApiPath.BROADCAST_EVENTS}, received {len(req.events)} event(s)")
    for event in req.events:
        background.add_task(node.processor.handle_event, event)


@app.post(ApiPath.POLL_EVENTS)
def poll_events(req: PollEvents) -> EventsPayload:
    logger.info(f"Request to {ApiPath.POLL_EVENTS}")
    events = node.network.flush_poll_queue(req.rid)
    return EventsPayload(events=events)


@app.post(ApiPath.FETCH_RIDS)
def fetch_rids(req: FetchRids) -> RidsPayload:
    logger.info(f"Request to {ApiPath.FETCH_RIDS}, allowed types {req.rid_types}")
    rids = node.cache.read_all_rids(req.rid_types)
    return RidsPayload(rids=rids)


@app.post(ApiPath.FETCH_MANIFESTS)
def fetch_manifests(req: FetchManifests) -> ManifestsPayload:
    logger.info(f"Request to {ApiPath.FETCH_MANIFESTS}, allowed types {req.rid_types}, rids {req.rids}")
    manifests: list[Manifest] = []
    not_found: list[RID] = []
    
    for rid in (req.rids or node.cache.read_all_rids(req.rid_types)):
        bundle = node.cache.read(rid)
        if bundle:
            manifests.append(bundle.manifest)
        else:
            not_found.append(rid)
    
    return ManifestsPayload(manifests=manifests, not_found=not_found)


@app.post(ApiPath.FETCH_BUNDLES)
def fetch_bundles(req: FetchBundles) -> BundlesPayload:
    logger.info(f"Request to {ApiPath.FETCH_BUNDLES}, requested rids {req.rids}")
    bundles: list[Bundle] = []
    not_found: list[RID] = []
    
    for rid in req.rids:
        bundle = node.cache.read(rid)
        if bundle:
            bundles.append(bundle)
        else:
            not_found.append(rid)
        
    return BundlesPayload(bundles=bundles, not_found=not_found)