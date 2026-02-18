from pydantic import model_validator
from .base import BaseNodeConfig
from .models import ServerConfig, KoiNetConfig as BaseKoiNetConfig
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
