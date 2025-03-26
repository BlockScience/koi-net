from rid_lib.ext import Cache, Bundle
from rid_lib.types.koi_net_node import KoiNetNode
from koi_net.protocol import NodeModel
from .network import NetworkInterface
from .processor import ProcessorInterface, default_handlers
from .reference import NodeReference


class NodeInterface:
    def __init__(
        self, 
        rid: KoiNetNode,
        profile: NodeModel,
        cache: Cache | None = None,
        network: NetworkInterface | None = None,
        processor: ProcessorInterface | None = None,
    ):
        self.cache = cache or Cache("cache")
        self.my = NodeReference(rid, profile, cache)
        self.network = network or NetworkInterface("event_queues.json", self.cache, self.my)
        self.processor = processor or ProcessorInterface(self.cache, self.network, self.my,
            default_handlers=[
                default_handlers.basic_state_handler,
                default_handlers.koi_net_graph_handler,
                default_handlers.edge_negotiation_handler
            ]
        )
        
        self.processor.handle_bundle(Bundle.generate(
            rid, profile.model_dump()))