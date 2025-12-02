import structlog
from rid_lib.types import KoiNetNode
from koi_net.config.core import NodeConfig
from koi_net.handshaker import Handshaker
from koi_net.network.graph import NetworkGraph
from koi_net.sync_manager import SyncManager

log = structlog.stdlib.get_logger()


class CatcherUpper:
    def __init__(
        self,
        graph: NetworkGraph,
        sync_manager: SyncManager,
        handshaker: Handshaker,
        config: NodeConfig
    ):
        self.graph = graph
        self.sync_manager = sync_manager
        self.handshaker = handshaker
        self.config = config
        
    def start(self):
        node_providers = self.graph.get_neighbors(
            direction="in",
            allowed_type=KoiNetNode
        )
        
        if node_providers:
            log.debug(f"Catching up with `orn:koi-net.node` providers: {node_providers}")
            self.sync_manager.catch_up_with(node_providers, [KoiNetNode])
        
        elif self.config.koi_net.first_contact.rid:
            log.debug(f"No edges with `orn:koi-net.node` providers, reaching out to first contact {self.config.koi_net.first_contact.rid!r}")
            self.handshaker.handshake_with(self.config.koi_net.first_contact.rid)