from rid_lib.ext import Cache

from .network.graph import NetworkGraph
from .network.request_handler import RequestHandler
from .processor.kobj_queue import KobjQueue
from .protocol.api_models import ErrorResponse
from .protocol.node import NodeProfile, NodeType


class SyncManager:
    """Handles state synchronization actions with other nodes."""
    graph: NetworkGraph
    cache: Cache
    request_handler: RequestHandler
    kobj_queue: KobjQueue
    
    def __init__(
        self,
        graph: NetworkGraph,
        cache: Cache,
        request_handler: RequestHandler,
        kobj_queue: KobjQueue
    ):
        self.graph = graph
        self.cache = cache
        self.request_handler = request_handler
        self.kobj_queue = kobj_queue
    
    def catch_up_with(self, nodes, rid_types):
        """Catches up with the state of RID types within other nodes."""
    
        for node in nodes:
            node_bundle = self.cache.read(node)
            node_profile = node_bundle.validate_contents(NodeProfile)
            
            # can't catch up with partial nodes
            if node_profile.node_type != NodeType.FULL:
                continue
            
            payload = self.request_handler.fetch_manifests(
                node, rid_types=rid_types)
            
            if type(payload) is ErrorResponse:
                continue
            
            for manifest in payload.manifests:
                self.kobj_queue.push(
                    manifest=manifest,
                    source=node
                )