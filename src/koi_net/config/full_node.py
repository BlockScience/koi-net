from pydantic import model_validator

from ..protocol import NodeProfile, NodeType
from .base import BaseNodeConfig
from .server_config import ServerConfig


class FullNodeProfile(NodeProfile):
    """Node profile config class for full nodes."""
    node_type: NodeType = NodeType.FULL

class FullNodeConfig(BaseNodeConfig):
    """Node config class for full nodes."""
    server: ServerConfig = ServerConfig()
    
    @model_validator(mode="after")
    def check_url(self):
        """Generates base URL if missing from node profile."""
        if not self.koi_net.node_profile.base_url:
            self.koi_net.node_profile.base_url = self.server.url
        return self
