import structlog
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from fastapi.responses import JSONResponse

from .base import EntryPoint
from ..network.response_handler import ResponseHandler
from ..protocol.model_map import API_MODEL_MAP
from ..protocol.api_models import ErrorResponse
from ..protocol.errors import ProtocolError
from ..lifecycle import NodeLifecycle
from ..config.full_node import FullNodeConfig

log = structlog.stdlib.get_logger()


class NodeServer(EntryPoint):
    """Entry point for full nodes, manages FastAPI server."""
    config: FullNodeConfig
    lifecycle: NodeLifecycle
    response_handler: ResponseHandler
    app: FastAPI
    router: APIRouter
    
    def __init__(
        self,
        config: FullNodeConfig,
        # lifecycle: NodeLifecycle,
        response_handler: ResponseHandler,
    ):
        self.config = config
        # self.lifecycle = lifecycle
        self.response_handler = response_handler
        
    def build_endpoints(self, router: APIRouter):
        """Builds endpoints for API router."""
        for path, models in API_MODEL_MAP.items():
            def create_endpoint(path: str):
                async def endpoint(req):
                    return self.response_handler.handle_response(path, req)
                
                # programmatically setting type hint annotations for FastAPI's model validation 
                endpoint.__annotations__ = {
                    "req": models.request_envelope,
                    "return": models.response_envelope
                }
                
                return endpoint
            
            router.add_api_route(
                path=path,
                endpoint=create_endpoint(path),
                methods=["POST"],
                response_model_exclude_none=True
            )
    
    def build_app(self):
        """Builds FastAPI app."""
        self.app = FastAPI(
            title="KOI-net Protocol API",
            version="1.1.0"
        )
        
        self.app.add_exception_handler(ProtocolError, self.protocol_error_handler)
        self.router = APIRouter(prefix="/koi-net")
        self.build_endpoints(self.router)
        self.app.include_router(self.router)
        
    def protocol_error_handler(self, request, exc: ProtocolError):
        """Catches `ProtocolError` and returns an `ErrorResponse` payload."""
        log.error(exc)
        resp = ErrorResponse(error=exc.error_type)
        log.info(f"Returning error response: {resp}")
        return JSONResponse(
            status_code=400,
            content=resp.model_dump(mode="json")
        )
    
    def run(self):
        """Starts FastAPI server and event handler."""
        
        # with self.lifecycle.run():
        self.build_app()
        
        uvicorn.run(
            app=self.app,
            host=self.config.server.host,
            port=self.config.server.port,
            log_config=None,
            access_log=False
        )