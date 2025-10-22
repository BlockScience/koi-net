import logging
from rich.logging import RichHandler
from rid_lib.types import KoiNetNode, KoiNetEdge
from koi_net.config.full_node import (
    FullNodeConfig, 
    ServerConfig, 
    KoiNetConfig, 
    NodeProfile, 
    NodeProvides
)
from koi_net.core import FullNode
from koi_net.processor.context import HandlerContext
from koi_net.processor.handler import HandlerType, KnowledgeHandler
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


class CoordinatorConfig(FullNodeConfig):
    server: ServerConfig = ServerConfig(port=8080)
    koi_net: KoiNetConfig = KoiNetConfig(
        node_name="coordinator",
        node_profile=NodeProfile(
            provides=NodeProvides(
                event=[KoiNetNode, KoiNetEdge],
                state=[KoiNetNode, KoiNetEdge]
            )
        ),
        rid_types_of_interest=[KoiNetNode, KoiNetEdge]
    )

@KnowledgeHandler.create(
    HandlerType.Network, 
    rid_types=[KoiNetNode])
def handshake_handler(ctx: HandlerContext, kobj: KnowledgeObject):
    logger.info("Handling node handshake")

    # only respond if node declares itself as NEW
    if kobj.event_type != EventType.NEW:
        return
        
    logger.info("Sharing this node's bundle with peer")
    identity_bundle = ctx.cache.read(ctx.identity.rid)
    ctx.event_queue.push(
        event=Event.from_bundle(EventType.NEW, identity_bundle),
        target=kobj.rid
    )
    
    logger.info("Proposing new edge")    
    # defer handling of proposed edge
    
    edge_bundle = generate_edge_bundle(
        source=kobj.rid,
        target=ctx.identity.rid,
        edge_type=EdgeType.WEBHOOK,
        rid_types=[KoiNetNode, KoiNetEdge]
    )
        
    ctx.kobj_queue.push(rid=edge_bundle.rid, event_type=EventType.FORGET)
    ctx.kobj_queue.push(bundle=edge_bundle)

class CoordinatorNode(FullNode):
    config = CoordinatorConfig
    knowledge_handlers = FullNode.knowledge_handlers + [handshake_handler]

if __name__ == "__main__":
    node = CoordinatorNode()
    node.entrypoint.run()