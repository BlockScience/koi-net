import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from rid_lib import RID
from rid_lib.ext import Manifest, Bundle
from koi_net.protocol.api_models import (
    PollEvents,
    FetchRids,
    FetchManifests,
    FetchBundles,
    EventsPayload,
    RidsPayload,
    ManifestsPayload,
    BundlesPayload
)
from koi_net.protocol.consts import (
    BROADCAST_EVENTS_PATH,
    POLL_EVENTS_PATH,
    FETCH_RIDS_PATH,
    FETCH_MANIFESTS_PATH,
    FETCH_BUNDLES_PATH
)
from .core import node
from .config import api_prefix

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):    
    yield
    
    node.network.save_queues()

app = FastAPI(lifespan=lifespan, root_path=api_prefix)

@app.post(BROADCAST_EVENTS_PATH)
def broadcast_events(req: EventsPayload, background: BackgroundTasks):
    logger.info(f"Request to {BROADCAST_EVENTS_PATH}, received {len(req.events)} event(s)")
    for event in req.events:
        background.add_task(node.processor.handle_event, event)


@app.post(POLL_EVENTS_PATH)
def poll_events(req: PollEvents) -> EventsPayload:
    logger.info(f"Request to {POLL_EVENTS_PATH}")
    events = node.network.flush_poll_queue(req.rid)
    return EventsPayload(events=events)


@app.post(FETCH_RIDS_PATH)
def fetch_rids(req: FetchRids) -> RidsPayload:
    logger.info(f"Request to {FETCH_RIDS_PATH}, allowed types {req.rid_types}")
    rids = node.cache.list_rids(req.rid_types)
    return RidsPayload(rids=rids)


@app.post(FETCH_MANIFESTS_PATH)
def fetch_manifests(req: FetchManifests) -> ManifestsPayload:
    logger.info(f"Request to {FETCH_MANIFESTS_PATH}, allowed types {req.rid_types}, rids {req.rids}")
    manifests: list[Manifest] = []
    not_found: list[RID] = []
    
    for rid in (req.rids or node.cache.list_rids(req.rid_types)):
        bundle = node.cache.read(rid)
        if bundle:
            manifests.append(bundle.manifest)
        else:
            not_found.append(rid)
    
    return ManifestsPayload(manifests=manifests, not_found=not_found)


@app.post(FETCH_BUNDLES_PATH)
def fetch_bundles(req: FetchBundles) -> BundlesPayload:
    logger.info(f"Request to {FETCH_BUNDLES_PATH}, requested rids {req.rids}")
    bundles: list[Bundle] = []
    not_found: list[RID] = []
    
    for rid in req.rids:
        bundle = node.cache.read(rid)
        if bundle:
            bundles.append(bundle)
        else:
            not_found.append(rid)
        
    return BundlesPayload(manifests=bundles, not_found=not_found)