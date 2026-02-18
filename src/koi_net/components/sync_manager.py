from dataclasses import dataclass
from logging import Logger
from rid_lib.ext import Cache
from rid_lib.types import KoiNetNode

from ..build.component import depends_on
from ..exceptions import RequestError
from .graph import NetworkGraph
from .request_handler import RequestHandler
from .kobj_queue import KobjQueue
from ..protocol.node import NodeProfile, NodeType


@dataclass
class SyncManager:
    """Handles state synchronization actions with other nodes."""
    
    log: Logger
    graph: NetworkGraph
    cache: Cache
    request_handler: RequestHandler
    kobj_queue: KobjQueue
    
    @depends_on("graph", "kobj_worker")
    def start(self):
        """Catches up with node providers on startup."""
        
        node_providers = self.graph.get_neighbors(
            direction="in",
            allowed_type=KoiNetNode
        )
        
        if not node_providers:
            return
        
        self.log.debug(f"Catching up with `orn:koi-net.node` providers: {node_providers}")
        self.catch_up_with(node_providers, [KoiNetNode])
    
    def catch_up_with(self, nodes, rid_types):
        """Catches up with the state of RID types within other nodes."""
    
        for node in nodes:
            node_bundle = self.cache.read(node)
            node_profile = node_bundle.validate_contents(NodeProfile)
            
            # can't catch up with partial nodes
            if node_profile.node_type != NodeType.FULL:
                continue
            
            try:
                payload = self.request_handler.fetch_manifests(
                    node, rid_types=rid_types)
            except RequestError:
                continue
            
            for manifest in payload.manifests:
                self.kobj_queue.push(
                    manifest=manifest,
                    source=node
                )