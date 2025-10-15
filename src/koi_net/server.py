import structlog
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from fastapi.responses import JSONResponse

from koi_net.interfaces.entrypoint import EntryPoint

from .network.response_handler import ResponseHandler
from .protocol.model_map import API_MODEL_MAP
from .protocol.api_models import ErrorResponse
from .protocol.errors import ProtocolError
from .lifecycle import NodeLifecycle
from .config import NodeConfig

log = structlog.stdlib.get_logger()


class NodeServer(EntryPoint):
    """Manages FastAPI server and event handling for full nodes."""
    config: NodeConfig
    lifecycle: NodeLifecycle
    response_handler: ResponseHandler
    app: FastAPI
    router: APIRouter
    
    def __init__(
        self,
        config: NodeConfig,
        lifecycle: NodeLifecycle,
        response_handler: ResponseHandler,
    ):
        self.config = config
        self.lifecycle = lifecycle
        self.response_handler = response_handler
        self._build_app()
        
    def _build_app(self):
        """Builds FastAPI app and adds endpoints."""
        @asynccontextmanager
        async def lifespan(*args, **kwargs):
            async with self.lifecycle.async_run():
                yield
        
        self.app = FastAPI(
            lifespan=lifespan, 
            title="KOI-net Protocol API",
            version="1.0.0"
        )
        
        self.app.add_exception_handler(ProtocolError, self.protocol_error_handler)
        
        self.router = APIRouter(prefix="/koi-net")
        
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
            
            self.router.add_api_route(
                path=path,
                endpoint=create_endpoint(path),
                methods=["POST"],
                response_model_exclude_none=True
            )
        
        self.app.include_router(self.router)
        
    def protocol_error_handler(self, request, exc: ProtocolError):
        """Catches `ProtocolError` and returns as `ErrorResponse`."""
        log.info(f"caught protocol error: {exc}")
        resp = ErrorResponse(error=exc.error_type)
        log.info(f"returning error response: {resp}")
        return JSONResponse(
            status_code=400,
            content=resp.model_dump(mode="json")
        )
    
    def run(self):
        """Starts FastAPI server and event handler."""
        uvicorn.run(
            app=self.app,
            host=self.config.server.host,
            port=self.config.server.port,
            log_config=None,
            access_log=False
        )