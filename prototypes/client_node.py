import httpx
import uvicorn
from koi_net import NodeModel, EdgeModel, NodeType, Provides, cache_compare, EventArrayModel
from koi_net.rid_types import KoiNetEdge, KoiNetNode
from rid_lib import RID
from rid_lib.ext import Bundle, Event, EventType, Manifest, Cache
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter


cache = Cache("client_cache")
network_cache = Cache("client_network_cache")

node_rid = KoiNetNode("test_client_node_id")
provider_url = "http://127.0.0.1:8000/koi-net"


@asynccontextmanager
async def lifespan(server: FastAPI):
    node_profile = NodeModel(
        node_type=NodeType.FULL,
        base_url="http://127.0.0.1:5000/koi-net",
        provides=Provides()
    )

    node_profile_bundle = Bundle(
        manifest=Manifest.generate(node_rid, node_profile.model_dump()),
        contents=node_profile.model_dump()
    )
        
    event = cache_compare(network_cache, node_profile_bundle)
    if event is not None:
        network_cache.write(node_profile_bundle)

    print("shaking hands with node at", provider_url)
    resp = httpx.post(provider_url + "/handshake", data=node_profile_bundle.model_dump_json())
    
    partner_bundle = Bundle(**resp.json())
    
    network_cache.write(partner_bundle)
    print("other node's RID is", partner_bundle.manifest.rid)
    
    negotiate_edge(partner_bundle.manifest.rid)

    yield

def negotiate_edge(partner_node_rid: KoiNetNode):
    print("proposing new edge agreement with", partner_node_rid)
    edge_profile = EdgeModel(
        source=partner_node_rid,
        target=node_rid,
        comm_type="webhook",
        contexts=["orn:slack.message"],
        status="proposed"
    )

    edge_rid = KoiNetEdge("test_edge_id")

    event = Event(
        rid=edge_rid,
        event_type=EventType.NEW,
        bundle=Bundle(
            manifest=Manifest.generate(edge_rid, edge_profile.model_dump()),
            contents=edge_profile.model_dump()
        )
    )
    
    bundle = network_cache.read(partner_node_rid)
    if not bundle:
        print("edge partner bundle not found")
        return
    
    partner_node_profile = NodeModel(**bundle.contents)


    events_json = EventArrayModel([event]).model_dump_json()    

    httpx.post(partner_node_profile.base_url + "/events/broadcast", data=events_json)


server = FastAPI(lifespan=lifespan)
koi_router = APIRouter(
    prefix="/koi-net"
)


@koi_router.post("/events/broadcast")
def listen_to_events(events: list[Event]):
    for event in events:
        handle_incoming_event(event)
        
def handle_incoming_event(event: Event):
    print("handling incoming event:", event.event_type, event.rid)
    if event.rid.context == KoiNetEdge.context:
        if event.bundle is None or event.bundle.contents is None:
            print("bundle not provided")
            return
            
        edge = EdgeModel(**event.bundle.contents)
        if edge.target == node_rid:
            if edge.status == "approved": 
                network_cache.write(event.bundle)
                print(edge.source, "approved edge agreement, writing updated bundle to cache")
    else:
        cache.write(event.bundle)
    
server.include_router(koi_router)

if __name__ == "__main__":
    uvicorn.run("client_node:server", port=5000)