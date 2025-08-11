import logging
from rich.logging import RichHandler
from pydantic import Field
from rid_lib.types import KoiNetNode, KoiNetEdge
from koi_net.config import NodeConfig, KoiNetConfig
from koi_net.protocol.node import NodeProfile, NodeProvides, NodeType
from koi_net import NodeInterface
from koi_net.context import HandlerContext
from koi_net.processor.handler import HandlerType
from koi_net.processor.knowledge_object import KnowledgeObject
from koi_net.protocol.event import Event, EventType
from koi_net.protocol.edge import EdgeType, generate_edge_bundle

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[RichHandler()]
)

logging.getLogger("koi_net").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

class CoordinatorConfig(NodeConfig):
    koi_net: KoiNetConfig = Field(default_factory = lambda:
        KoiNetConfig(
            node_name="coordinator",
            node_profile=NodeProfile(
                node_type=NodeType.FULL,
                provides=NodeProvides(
                    event=[KoiNetNode, KoiNetEdge],
                    state=[KoiNetNode, KoiNetEdge]
                )
            ),
            cache_directory_path=".coordinator_rid_cache",
            event_queues_path="coordinator_event_queues.json",
            private_key_pem_path="coordinator_priv_key.pem"
        )
    )
    
node = NodeInterface(
    config=CoordinatorConfig.load_from_yaml("coordinator_config.yaml"),
    use_kobj_processor_thread=True
)

@node.processor.pipeline.register_handler(HandlerType.Network, rid_types=[KoiNetNode])
def handshake_handler(ctx: HandlerContext, kobj: KnowledgeObject):
    logger.info("Handling node handshake")

    # only respond if node declares itself as NEW
    if kobj.event_type != EventType.NEW:
        return
        
    logger.info("Sharing this node's bundle with peer")
    identity_bundle = ctx.effector.deref(ctx.identity.rid)
    ctx.event_queue.push_event_to(
        event=Event.from_bundle(EventType.NEW, identity_bundle),
        node=kobj.rid,
        flush=True
    )
    
    logger.info("Proposing new edge")    
    # defer handling of proposed edge
    
    edge_bundle = generate_edge_bundle(
        source=kobj.rid,
        target=ctx.identity.rid,
        edge_type=EdgeType.WEBHOOK,
        rid_types=[KoiNetNode, KoiNetEdge]
    )
        
    ctx.handle(rid=edge_bundle.rid, event_type=EventType.FORGET)
    ctx.handle(bundle=edge_bundle)
    
if __name__ == "__main__":
    node.server.run()