from pydantic import BaseModel, model_validator
from .base import BaseNodeConfig, KoiNetConfig as BaseKoiNetConfig
from ..protocol.node import (
    NodeProfile as BaseNodeProfile, 
    NodeType, 
    NodeProvides
)


class NodeProfile(BaseNodeProfile):
    """Node profile config class for full nodes."""
    node_type: NodeType = NodeType.FULL

class KoiNetConfig(BaseKoiNetConfig):
    """KOI-net config class for full nodes."""
    node_profile: NodeProfile

class ServerConfig(BaseModel):
    """Server config for full nodes.
    
    The parameters in this class represent how a server should be hosted,
    not accessed. For example, a node may host a server at
    `http://127.0.0.1:8000/koi-net`, but serve through nginx at
    `https://example.com/koi-net`.
    """
    
    host: str = "127.0.0.1"
    port: int = 8000
    path: str | None = "/koi-net"
    
    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}{self.path or ''}"

class FullNodeConfig(BaseNodeConfig):
    """Node config class for full nodes."""
    koi_net: KoiNetConfig
    server: ServerConfig = ServerConfig()
    
    @model_validator(mode="after")
    def check_url(self):
        """Generates base URL if missing from node profile."""
        if not self.koi_net.node_profile.base_url:
            self.koi_net.node_profile.base_url = self.server.url
        return self
