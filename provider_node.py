from rid_lib import RID
import random
import httpx
from fastapi import BackgroundTasks, FastAPI, APIRouter
import uvicorn
from rid_lib.types import SlackMessage, SlackChannel, SlackUser
from rid_lib.ext import Cache, utils, Event, EventType, Bundle, Manifest
from contextlib import asynccontextmanager
from koi_net import Node, NodeType, Provides, Edge, cache_compare, EventArray
from pydantic import BaseModel
from rid_types import KoiNetEdge, KoiNetNode
from rid_lib.ext.pydantic_adapter import RIDField

cache = Cache("cache")
network_cache = Cache("network_cache")

node_rid = KoiNetNode("test_provider_node_id")


@asynccontextmanager
async def lifespan(server: FastAPI):
    node_profile = Node(
        base_url="http://127.0.0.1:8000/koi-net",
        node_type=NodeType.FULL,
        provides=Provides(
            event=[SlackMessage.context],
            state=[SlackChannel.context, SlackMessage.context]
        )
    )
    
    node_profile_bundle = Bundle(
        manifest=Manifest.generate(node_rid, node_profile.model_dump()),
        contents=node_profile.model_dump()
    )
            
    event = cache_compare(network_cache, node_profile_bundle)
    print("NO CHANGE" if event is None else event)
        
    if event is not None:
        network_cache.write(node_profile_bundle)

    yield
    

server = FastAPI(lifespan=lifespan)
koi_router = APIRouter(
    prefix="/koi-net"
)

# network configuration
@koi_router.post("/handshake")
def get_profile(partner_bundle: Bundle):
    network_cache.write(partner_bundle)
    print(f"handshaking with {partner_bundle.manifest.rid}")
    bundle = network_cache.read(node_rid)
    if not bundle: return
    return bundle

@koi_router.get("/events/poll")
def poll_events(rid: RIDField) -> list[Event]:
    print(rid)
    return []

@koi_router.post("/events/broadcast")
def listen_to_events(events: list[Event], background: BackgroundTasks):
    for event in events:
        background.add_task(handle_incoming_event, event)


            

def handle_incoming_event(event: Event):
    print("handling incoming event:", event.event_type, event.rid)
    if event.rid.context == KoiNetEdge.context:
        if event.bundle is None or event.bundle.contents is None:
            print("bundle not provided")
            return
            
        edge = Edge(**event.bundle.contents)
        if edge.source == node_rid:
            if edge.status != "proposed": 
                print("edge status is not 'proposed', ignoring")
                return
            
            print(edge.source, "proposed a new edge agreement, approving and returning")
            
            edge.status = "approved"
            
            updated_bundle = Bundle(
                manifest=Manifest.generate(event.bundle.manifest.rid, edge.model_dump()),
                contents=edge.model_dump()
            )
            
            network_cache.write(updated_bundle)
            
            target_node_bundle = network_cache.read(edge.target)
            if target_node_bundle is None:
                print("edge partner bundle not found")
                return

            target_node_profile = Node(**target_node_bundle.contents)
            
            event = Event(
                rid=event.rid,
                event_type=EventType.UPDATE,
                bundle=updated_bundle
            )
            
            events_json = EventArray([event]).model_dump_json()
            
            httpx.post(target_node_profile.base_url + "/events/broadcast", data=events_json)
            
def handle_outgoing_event(event: Event, i):
    print(i, event.rid)
    
    network_rids = network_cache.read_all_rids()
    
    subscribers = []
    
    for rid in network_rids:
        if rid.context == KoiNetEdge.context:
            bundle = network_cache.read(rid)
            edge = Edge(**bundle.contents)
            if edge.source == node_rid and event.rid.context in edge.contexts:
                subscribers.append((edge.target, edge.comm_type))
    
    for sub_rid, comm_type in subscribers:
        bundle = network_cache.read(sub_rid)
        node = Node(**bundle.contents)
        if comm_type == "webhook":
            events_json = EventArray([event]).model_dump_json()

            httpx.post(node.base_url + "/events/broadcast", data=events_json)
            
        elif comm_type == "poll":
            ...


class RetrieveRids(BaseModel):
    contexts: list[str] = []

@koi_router.post("/state/rids")
def retrieve_rids(retrieve: RetrieveRids = RetrieveRids()):
    all_rids = cache.read_all_rids()
    
    rids = []
    for rid in all_rids:
        if not retrieve.contexts or rid.context in retrieve.contexts:
            rids.append(str(rid))
    
    return rids    
    
class RetrieveManifests(BaseModel):
    contexts: list[str] = []
    rids: list[str] = []
    
@koi_router.post("/state/manifests")
def retrieve_manifests(retrieve: RetrieveManifests = RetrieveManifests()):
    rids = retrieve.rids or cache.read_all_rids()
    
    manifests = []
    for rid in rids:
        bundle = cache.read(rid)
        if bundle is None: continue
        
        if not retrieve.contexts or rid.context in retrieve.contexts:
            manifests.append(bundle.manifest)
    
    return manifests    


class RetrieveBundles(BaseModel):
    rids: list[RIDField]
    
@koi_router.post("/state/bundles")
def retrieve_bundles(retrieve: RetrieveBundles) -> list[Bundle]:
    print(retrieve)
    bundles = []
    for rid in retrieve.rids:
        print(rid)
        bundle = cache.read(rid)
        if not bundle: continue
        bundles.append(bundle)
    
    return bundles
    
server.include_router(koi_router)

@server.post("/event_simulator")
def test(background: BackgroundTasks):
    rids = random.choices(cache.read_all_rids(), k=5)
    
    for i, event in enumerate([
        Event(
            rid=rid,
            event_type=EventType.NEW,
            bundle=cache.read(rid)
        )
        for rid in rids
    ]):
        background.add_task(handle_outgoing_event, event, i)
    
if __name__ == "__main__":
    uvicorn.run("provider_node:server")