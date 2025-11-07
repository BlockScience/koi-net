from pydantic import BaseModel, model_validator
from koi_net.config.core import NodeConfig, KoiNetConfig as BaseKoiNetConfig
from ..protocol.node import NodeProfile as BaseNodeProfile, NodeType, NodeProvides


class NodeProfile(BaseNodeProfile):
    node_type: NodeType = NodeType.FULL

class KoiNetConfig(BaseKoiNetConfig):
    node_profile: NodeProfile

class ServerConfig(BaseModel):
    """Config for the node server (full node only)."""
    
    host: str = "127.0.0.1"
    port: int = 8000
    path: str | None = "/koi-net"
    
    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}{self.path or ''}"

class FullNodeConfig(NodeConfig):
    koi_net: KoiNetConfig
    server: ServerConfig = ServerConfig()
    
    @model_validator(mode="after")
    def check_url(self):
        if not self.koi_net.node_profile.base_url:
            self.koi_net.node_profile.base_url = self.server.url
        return self
