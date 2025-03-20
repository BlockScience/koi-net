from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from rid_lib import RID
from koi_net.models import *
from .core import node
from .config import api_prefix

@asynccontextmanager
async def lifespan(app: FastAPI):    
    yield
    
    node.network.save_queues()

app = FastAPI(lifespan=lifespan, root_path=api_prefix)

@app.post(ApiPath.BROADCAST_EVENTS)
def broadcast_events(req: EventsPayload, background: BackgroundTasks):
    for event in req.events:
        background.add_task(node.processor.handle_event, event)


@app.post(ApiPath.POLL_EVENTS)
def poll_events(req: PollEvents) -> EventsPayload:
    events = node.network.flush_poll_queue(req.rid)
    return EventsPayload(events=events)


@app.post(ApiPath.FETCH_RIDS)
def fetch_rids(req: FetchRids) -> RidsPayload:
    rids = node.cache.read_all_rids(req.allowed_types)
    return RidsPayload(rids=rids)


@app.post(ApiPath.FETCH_MANIFESTS)
def fetch_manifests(req: FetchManifests) -> ManifestsPayload:
    manifests: list[Manifest] = []
    not_found: list[RID] = []
    
    for rid in (req.rids or node.cache.read_all_rids(req.allowed_types)):
        bundle = node.cache.read(rid)
        if bundle:
            manifests.append(bundle.manifest)
        else:
            not_found.append(rid)
    
    return ManifestsPayload(manifests=manifests, not_found=not_found)


@app.post(ApiPath.FETCH_BUNDLES)
def fetch_bundles(req: FetchBundles) -> BundlesPayload:
    bundles: list[Bundle] = []
    not_found: list[RID] = []
    
    for rid in req.rids:
        bundle = node.cache.read(rid)
        if bundle:
            bundles.append(bundle)
        else:
            not_found.append(rid)
        
    return BundlesPayload(bundles=bundles, not_found=not_found)