from rid_lib.ext import Cache, Bundle
from rid_lib.types.koi_net_node import KoiNetNode
from koi_net.protocol import NodeModel
from .network import NetworkInterface
from .processor import ProcessorInterface, default_handlers
from .processor.interface import Handler
from .identity import NodeIdentity


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
        self.identity = NodeIdentity(rid, profile, cache)
        self.network = network or NetworkInterface("event_queues.json", self.cache, self.identity)
        
        # pull all handlers defined in default_handlers module
        handlers = [
            obj for obj in vars(default_handlers).values() 
            if isinstance(obj, Handler)
        ]
        
        self.processor = processor or ProcessorInterface(self.cache, self.network, self.identity, handlers)
        
        self.processor.handle_bundle(Bundle.generate(
            rid, profile.model_dump()))