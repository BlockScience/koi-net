import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from fastapi.responses import JSONResponse
from .network.event_queue import NetworkEventQueue
from .network.response_handler import ResponseHandler
from .processor.interface import ProcessorInterface
from .protocol.api_models import (
    PollEvents,
    FetchRids,
    FetchManifests,
    FetchBundles,
    EventsPayload,
    RidsPayload,
    ManifestsPayload,
    BundlesPayload,
    ErrorResponse
)
from .protocol.errors import ProtocolError
from .protocol.envelope import SignedEnvelope
from .protocol.consts import (
    BROADCAST_EVENTS_PATH,
    POLL_EVENTS_PATH,
    FETCH_RIDS_PATH,
    FETCH_MANIFESTS_PATH,
    FETCH_BUNDLES_PATH
)
from .secure import Secure
from .lifecycle import NodeLifecycle
from .config import NodeConfig

logger = logging.getLogger(__name__)


class NodeServer:
    lifecycle: NodeLifecycle
    
    def __init__(
        self,
        config: NodeConfig,
        lifecycle: NodeLifecycle,
        secure: Secure,
        processor: ProcessorInterface,
        event_queue: NetworkEventQueue,
        response_handler: ResponseHandler
    ):
        self.config = config
        self.lifecycle = lifecycle
        self.secure = secure
        self.processor = processor
        self.event_queue = event_queue
        self.response_handler = response_handler
        self._build_app()
        
    def _build_app(self):
        
        @asynccontextmanager
        async def lifespan(*args, **kwargs):
            async with self.lifecycle.async_run():
                yield
        
        self.app = FastAPI(
            lifespan=lifespan, 
            title="KOI-net Protocol API",
            version="1.0.0"
        )
        
        self.router = APIRouter(prefix="/koi-net")
        self.app.add_exception_handler(ProtocolError, self.protocol_error_handler)
        
        def _add_endpoint(path, func):
            self.router.add_api_route(
                path=path,
                endpoint=self.secure.envelope_handler(func),
                methods=["POST"]
            )
        
        _add_endpoint(BROADCAST_EVENTS_PATH, self.broadcast_events)
        _add_endpoint(POLL_EVENTS_PATH, self.poll_events)
        _add_endpoint(FETCH_RIDS_PATH, self.fetch_rids)
        _add_endpoint(FETCH_MANIFESTS_PATH, self.fetch_manifests)
        _add_endpoint(FETCH_BUNDLES_PATH, self.fetch_bundles)
        
        self.app.include_router(self.router)
    
    def run(self):
        uvicorn.run(
            app=self.app,
            host=self.config.server.host,
            port=self.config.server.port
        )
        
    def protocol_error_handler(self, request, exc: ProtocolError):
        logger.info(f"caught protocol error: {exc}")
        resp = ErrorResponse(error=exc.error_type)
        logger.info(f"returning error response: {resp}")
        return JSONResponse(
            status_code=400,
            content=resp.model_dump(mode="json")
        )

    async def broadcast_events(self, req: SignedEnvelope[EventsPayload]):
        logger.info(f"Request to {BROADCAST_EVENTS_PATH}, received {len(req.payload.events)} event(s)")
        for event in req.payload.events:
            self.processor.handle(event=event, source=req.source_node)
        
    async def poll_events(
        self, req: SignedEnvelope[PollEvents]
    ) -> SignedEnvelope[EventsPayload] | ErrorResponse:
        logger.info(f"Request to {POLL_EVENTS_PATH}")
        events = self.event_queue.flush_poll_queue(req.source_node)
        return EventsPayload(events=events)

    async def fetch_rids(
        self, req: SignedEnvelope[FetchRids]
    ) -> SignedEnvelope[RidsPayload] | ErrorResponse:
        return self.response_handler.fetch_rids(req.payload, req.source_node)

    async def fetch_manifests(
        self, req: SignedEnvelope[FetchManifests]
    ) -> SignedEnvelope[ManifestsPayload] | ErrorResponse:
        return self.response_handler.fetch_manifests(req.payload, req.source_node)

    async def fetch_bundles(
        self, req: SignedEnvelope[FetchBundles]
    ) -> SignedEnvelope[BundlesPayload] | ErrorResponse:
        return self.response_handler.fetch_bundles(req.payload, req.source_node)
