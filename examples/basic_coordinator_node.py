import json
import logging
import uvicorn
from contextlib import asynccontextmanager
from rich.logging import RichHandler
from fastapi import FastAPI
from rid_lib.types import KoiNetNode, KoiNetEdge
from koi_net import NodeInterface
from koi_net.processor.handler import HandlerType
from koi_net.processor.knowledge_object import KnowledgeObject, KnowledgeSource
from koi_net.protocol.edge import EdgeType
from koi_net.protocol.event import Event, EventType
from koi_net.protocol.helpers import generate_edge_bundle
from koi_net.protocol.node import NodeProfile, NodeType, NodeProvides
from koi_net.processor import ProcessorInterface
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


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[RichHandler()]
)

logging.getLogger("koi_net").setLevel(logging.DEBUG)

port = 8000

node = NodeInterface(
    name="coordinator",
    profile=NodeProfile(
        base_url=f"http://127.0.0.1:{port}/koi-net",
        node_type=NodeType.FULL,
        provides=NodeProvides(
            event=[KoiNetNode, KoiNetEdge],
            state=[KoiNetNode, KoiNetEdge]
        )
    ),
    use_kobj_processor_thread=True,
    cache_directory_path="coordinator_node_rid_cache",
    event_queues_file_path="coordinator_node_event_queus.json",
    identity_file_path="coordinator_node_identity.json",
)


logger = logging.getLogger(__name__)


@node.processor.register_handler(HandlerType.Network, rid_types=[KoiNetNode])
def handshake_handler(proc: ProcessorInterface, kobj: KnowledgeObject):    
    logger.info("Handling node handshake")

    # only respond if node declares itself as NEW
    if kobj.event_type != EventType.NEW:
        return
        
    logger.info("Sharing this node's bundle with peer")
    proc.network.push_event_to(
        event=Event.from_bundle(EventType.NEW, proc.identity.bundle),
        node=kobj.rid,
        flush=True
    )
    
    logger.info("Proposing new edge")    
    # defer handling of proposed edge
    proc.handle(bundle=generate_edge_bundle(
        source=kobj.rid,
        target=proc.identity.rid,
        edge_type=EdgeType.WEBHOOK,
        rid_types=[KoiNetNode, KoiNetEdge]
    ))



@asynccontextmanager
async def lifespan(app: FastAPI):
    node.start()
    yield
    node.stop()

app = FastAPI(
    lifespan=lifespan, 
    root_path="/koi-net",
    title="KOI-net Protocol API",
    version="1.0.0"
)

@app.post(BROADCAST_EVENTS_PATH)
def broadcast_events(req: EventsPayload):
    logger.info(f"Request to {BROADCAST_EVENTS_PATH}, received {len(req.events)} event(s)")
    for event in req.events:
        node.processor.handle(event=event, source=KnowledgeSource.External)
    
@app.post(POLL_EVENTS_PATH)
def poll_events(req: PollEvents) -> EventsPayload:
    logger.info(f"Request to {POLL_EVENTS_PATH}")
    events = node.network.flush_poll_queue(req.rid)
    return EventsPayload(events=events)

@app.post(FETCH_RIDS_PATH)
def fetch_rids(req: FetchRids) -> RidsPayload:
    return node.network.response_handler.fetch_rids(req)

@app.post(FETCH_MANIFESTS_PATH)
def fetch_manifests(req: FetchManifests) -> ManifestsPayload:
    return node.network.response_handler.fetch_manifests(req)

@app.post(FETCH_BUNDLES_PATH)
def fetch_bundles(req: FetchBundles) -> BundlesPayload:
    return node.network.response_handler.fetch_bundles(req)
    
if __name__ == "__main__":
    openapi_spec = app.openapi()

    with open("koi-net-protocol-openapi.json", "w") as f:
        json.dump(openapi_spec, f, indent=2)
    
    uvicorn.run("examples.basic_coordinator_node:app", port=port)