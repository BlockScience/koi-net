import logging
import uvicorn
from contextlib import asynccontextmanager
from rich.logging import RichHandler
from fastapi import FastAPI
from rid_lib.types import KoiNetNode, KoiNetEdge
from koi_net import NodeInterface
from koi_net.processor.knowledge_object import KnowledgeSource

from koi_net.protocol.node import NodeProfile, NodeType, NodeProvides
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

logger = logging.getLogger(__name__)
logging.getLogger("koi_net").setLevel(logging.DEBUG)

port = 5000
coordinator_url = "http://127.0.0.1:8000/koi-net"

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
    first_contact=coordinator_url
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    node.start()
    yield
    node.stop()


app = FastAPI(lifespan=lifespan, root_path="/koi-net")

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
    # update this path to the Python module that defines "app"
    uvicorn.run("examples.full_node_template:app", port=port)