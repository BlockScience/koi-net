from dataclasses import dataclass

from rid_lib.types import KoiNetNode, KoiNetEdge
from koi_net.core import FullNode
from koi_net.config.full_node import (
    FullNodeConfig, 
    ServerConfig, 
    KoiNetConfig, 
    NodeProfile, 
    NodeProvides
)

from koi_net.components.interfaces import HandlerType, KnowledgeHandler
from koi_net.components import NodeIdentity, Cache, EventQueue, KobjQueue

from koi_net.protocol.event import Event, EventType
from koi_net.protocol.edge import EdgeType, generate_edge_bundle
from koi_net.protocol.knowledge_object import KnowledgeObject


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

@dataclass
class HandshakeHandler(KnowledgeHandler):
    identity: NodeIdentity
    cache: Cache
    event_queue: EventQueue
    kobj_queue: KobjQueue
    
    handler_type = HandlerType.Network
    rid_types = (KoiNetNode,)
    
    def handle(self, kobj: KnowledgeObject):
        # only respond if node declares itself as NEW
        if not (kobj.event_type == EventType.NEW and kobj.source == kobj.rid):
            return
        
        self.log.info("Handling node handshake")
            
        self.log.info("Sharing this node's bundle with peer")
        identity_bundle = self.cache.read(self.identity.rid)
        self.event_queue.push(
            event=Event.from_bundle(
                event_type=EventType.NEW, 
                bundle=identity_bundle),
            target=kobj.rid
        )
        
        self.log.info("Proposing new edge")
        # defer handling of proposed edge
        
        edge_bundle = generate_edge_bundle(
            source=kobj.rid,
            target=self.identity.rid,
            edge_type=EdgeType.WEBHOOK,
            rid_types=[KoiNetNode, KoiNetEdge]
        )
            
        self.kobj_queue.push(rid=edge_bundle.rid, event_type=EventType.FORGET)
        self.kobj_queue.push(bundle=edge_bundle)

class CoordinatorNode(FullNode):
    config_schema = CoordinatorConfig
    handshake_handler = HandshakeHandler

if __name__ == "__main__":
    CoordinatorNode().run()