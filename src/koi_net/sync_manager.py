from rid_lib.ext import Cache
from rid_lib.types import KoiNetNode

from koi_net.network.graph import NetworkGraph
from koi_net.network.request_handler import RequestHandler
from koi_net.processor.kobj_queue import KobjQueue
from .protocol.api_models import ErrorResponse
from .protocol.node import NodeProfile, NodeType


class SyncManager:
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
        
    def catch_up_with_coordinators(self) -> bool:
        return self.catch_up_with(
            nodes=self.graph.get_neighbors(
                direction="in",
                allowed_type=KoiNetNode
            ),
            rid_types=[KoiNetNode]
        )
    
    def catch_up_with(self, nodes, rid_types) -> bool:
        # get all of the nodes such that, (node) -[orn:koi-net.node]-> (me)
        # node providers that I am subscribed to
        if not nodes:
            return False
        
        for node in nodes:
            node_bundle = self.cache.read(node)
            node_profile = node_bundle.validate_contents(NodeProfile)
            
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
        
        return True