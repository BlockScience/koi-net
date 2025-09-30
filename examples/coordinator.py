import logging
from rich.logging import RichHandler
from pydantic import Field
from rid_lib.types import KoiNetNode, KoiNetEdge
from koi_net.config import NodeConfig, KoiNetConfig, ServerConfig
from koi_net.core import NodeAssembler
from koi_net.protocol.node import NodeProfile, NodeProvides, NodeType
from koi_net.context import HandlerContext
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


class CoordinatorConfig(NodeConfig):
    server: ServerConfig = Field(default_factory=lambda: 
        ServerConfig(port=8080)
    )
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
            rid_types_of_interest=[KoiNetNode, KoiNetEdge]
        )
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
    ctx.event_queue.push_event_to(
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
        
    ctx.kobj_queue.put_kobj(rid=edge_bundle.rid, event_type=EventType.FORGET)
    ctx.kobj_queue.put_kobj(bundle=edge_bundle)

class CoordinatorNodeAssembler(NodeAssembler):
    config = CoordinatorConfig
    knowledge_handlers = [
        *NodeAssembler.knowledge_handlers,
        handshake_handler
    ]


if __name__ == "__main__":
    node = CoordinatorNodeAssembler.create()
    node.server.run()