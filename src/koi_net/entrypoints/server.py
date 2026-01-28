import time
from logging import Logger
from typing import TYPE_CHECKING

from fastapi import Request
from structlog.contextvars import bound_contextvars

from ..logging_context import LoggingContext
from ..build.component import depends_on
from ..build.threaded_component import ThreadedComponent
from ..network.response_handler import ResponseHandler
from ..protocol.model_map import API_MODEL_MAP
from ..protocol.api_models import ErrorResponse
from ..protocol.errors import EXCEPTION_TO_ERROR_TYPE, ProtocolError
from ..config.full_node import FullNodeConfig

if TYPE_CHECKING:
    import uvicorn
    from fastapi import FastAPI, APIRouter


class NodeServer(ThreadedComponent):
    """Entry point for full nodes, manages FastAPI server."""
    config: FullNodeConfig
    response_handler: ResponseHandler
    app: "FastAPI"
    router: "APIRouter"
    server: "uvicorn.Server"
    
    def __init__(
        self,
        log: Logger,
        logging_context: LoggingContext,
        config: FullNodeConfig,
        response_handler: ResponseHandler
    ):
        super().__init__(log=log, logging_context=logging_context, name="server")
        self.config = config
        self.response_handler = response_handler
        
        self.build_app()
        
        self.server = None
        self.thread = None
        
    def build_endpoints(self, router: "APIRouter"):
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
        from fastapi import FastAPI, APIRouter
        from starlette.middleware.base import BaseHTTPMiddleware

        self.app = FastAPI(
            title="KOI-net Protocol API",
            version="1.1.0"
        )
        
        self.app.add_middleware(BaseHTTPMiddleware, dispatch=self.logging_middleware)
        self.app.add_exception_handler(ProtocolError, handler=self.protocol_error_handler)
        self.router = APIRouter(prefix="/koi-net")
        self.build_endpoints(self.router)
        self.app.include_router(self.router)
    
    async def logging_middleware(self, request: Request, call_next):
        """Binds contextvars per HTTP request, and emits access logs."""
        with self.logging_context.bound_vars(thread="server"):
            self.log.info(f"Request from {request.client.host}:{request.client.port} - {request.method} {request.url.path}")
            response = await call_next(request)
            self.log.info(f"Response code {response.status_code}")
            return response
        
    def protocol_error_handler(self, request, exc: ProtocolError):
        """Catches `ProtocolError` and returns an `ErrorResponse` payload."""
        from fastapi.responses import JSONResponse
        
        self.log.error(exc)
        resp = ErrorResponse(error=EXCEPTION_TO_ERROR_TYPE[type(exc)])
        self.log.info(f"Returning error response: {resp}")
        return JSONResponse(
            status_code=400,
            content=resp.model_dump(mode="json")
        )
    
    def run(self):
        self.server.run()
        
    @depends_on("port_manager")
    def start(self):
        import uvicorn
        self.server = uvicorn.Server(
            config=uvicorn.Config(
            app=self.app,
            host=self.config.server.host,
            port=self.config.server.port,
            log_config=None,
            access_log=False,
            lifespan="off"
        ))
        
        super().start()
        
        deadline = time.monotonic() + 10
        while not self.server.started:
            if time.monotonic() > deadline:
                raise RuntimeError("Server failed to start")
            time.sleep(0.1)
    
    def stop(self):
        if not self.server:
            return
        
        self.server.should_exit = True
        super().stop()