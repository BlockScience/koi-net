from fastapi import FastAPI, APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from rid_lib.ext import Bundle, Event
from rid_lib.ext.manifest import Manifest
from rid_lib.ext.pydantic_adapter import RIDField
from coordinator.event_handler import handle_incoming_event
from rid_types import KoiNetNode
from koi_net import Node, cache_compare
from .core import cache, network
from .config import this_node_rid
from .setup import lifespan


server = FastAPI(lifespan=lifespan)
koi_net_router = APIRouter(prefix="/koi-net")

class NodeBundle(Bundle):
    contents: Node

@koi_net_router.post("/handshake")
def handshake(peer_bundle: NodeBundle) -> NodeBundle:
    if peer_bundle.manifest.rid.context != KoiNetNode.context:
        raise Exception("Provided bundle must be a node profile")
    
    cache_state = cache_compare(cache, peer_bundle)
    # TODO: create and broadcast node profile events
    
    if cache_state:
        cache.write(peer_bundle)
        # TODO: handle event propagation to subscribers
        
    return cache.read(this_node_rid)


@koi_net_router.post("/events/broadcast")
def broadcast_events(events: list[Event], background: BackgroundTasks):
    for event in events:
        background.add_task(handle_incoming_event, event)

        
@koi_net_router.get("/events/poll")
def poll_events(rid: RIDField) -> list[Event]:
    events = network.sub_queue.poll.get(rid)
    if not events:
        return []
    
    network.sub_queue.poll[rid].clear()
    return events
    

class RetrieveRids(BaseModel):
    contexts: list[str] = []

@koi_net_router.post("/state/rids")
def retrieve_rids(retrieve: RetrieveRids = RetrieveRids()) -> list[RIDField]:
    return [
        rid for rid in cache.read_all_rids()
        if (
            not retrieve.contexts 
            or rid.context in retrieve.contexts
        )
    ]
    

class RetrieveManifests(BaseModel):
    contexts: list[str] = []
    rids: list[str] = []
    
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


class RetrieveBundles(BaseModel):
    rids: list[RIDField]
    
@koi_net_router.post("/state/bundles")
def retrieve_bundles(retrieve: RetrieveBundles) -> list[Bundle]:    
    return [
        bundle for rid in retrieve.rids
        if (bundle := cache.read(rid))
    ]


server.include_router(koi_net_router)