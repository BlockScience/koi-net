from fastapi import FastAPI, APIRouter, BackgroundTasks, HTTPException
from rid_lib.ext import Bundle, Event
from rid_lib.ext.manifest import Manifest
from rid_lib.ext.pydantic_adapter import RIDField
from rid_types import KoiNetNode
from .core import cache, network, processor
from .config import this_node_rid
from .setup import lifespan
from .network_models import *


server = FastAPI(lifespan=lifespan)
koi_net_router = APIRouter(prefix="/koi-net")


@koi_net_router.post("/handshake")
def handshake(peer_bundle: HandshakeModel) -> HandshakeModel:
    if peer_bundle.manifest.rid.context != KoiNetNode.context:
        raise Exception("Provided bundle must be a node profile")
    
    print("received handshake from", peer_bundle.manifest.rid)
    
    processor.handle_state(peer_bundle)
    return cache.read(this_node_rid)


@koi_net_router.post("/events/broadcast")
def broadcast_events(events: list[Event], background: BackgroundTasks):
    for event in events:
        print('added background task')
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


server.include_router(koi_net_router)