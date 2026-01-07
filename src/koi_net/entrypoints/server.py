import socket
import threading
import time
from typing import TYPE_CHECKING
import structlog

from koi_net.config.loader import ConfigLoader

from ..network.response_handler import ResponseHandler
from ..protocol.model_map import API_MODEL_MAP
from ..protocol.api_models import ErrorResponse
from ..protocol.errors import EXCEPTION_TO_ERROR_TYPE, ProtocolError
from ..config.full_node import FullNodeConfig

if TYPE_CHECKING:
    import uvicorn
    from fastapi import FastAPI, APIRouter


log = structlog.stdlib.get_logger()


class NodeServer:
    """Entry point for full nodes, manages FastAPI server."""
    _config: FullNodeConfig
    response_handler: ResponseHandler
    app: "FastAPI"
    router: "APIRouter"
    server: "uvicorn.Server"
    
    def __init__(
        self,
        config: FullNodeConfig,
        config_loader: ConfigLoader,
        response_handler: ResponseHandler
    ):
        self._config = config
        self.config_loader = config_loader
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
        from fastapi.responses import JSONResponse
        
        log.error(exc)
        resp = ErrorResponse(error=EXCEPTION_TO_ERROR_TYPE[type(exc)])
        log.info(f"Returning error response: {resp}")
        return JSONResponse(
            status_code=400,
            content=resp.model_dump(mode="json")
        )
    
    def acquire_port(self):
        derived_url = self._config.koi_net.node_profile.base_url == self._config.server.url
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            address = (self._config.server.host, self._config.server.port)
            while s.connect_ex(address) == 0:
                log.debug(f"port {address[1]} in use")
                self._config.server.port += 1
                address = (address[0], self._config.server.port)
        log.debug(f"acquired port {address[1]}")
        
        if derived_url:
            self._config.koi_net.node_profile.base_url = self._config.server.url
        
        self.config_loader.save_to_yaml()
    
    def start(self):
        self.acquire_port()
        
        import uvicorn
        self.server = uvicorn.Server(
            config=uvicorn.Config(
            app=self.app,
            host=self._config.server.host,
            port=self._config.server.port,
            log_config=None,
            lifespan="off"
        ))
        
        self.thread = threading.Thread(target=self.server.run)
        self.thread.start()
        
    def stop(self):
        if not self.server or not self.thread:
            return
        
        self.server.should_exit = True
        if self.thread.is_alive():
            self.thread.join()