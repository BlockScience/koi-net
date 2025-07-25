from .identity import NodeIdentity
from .protocol.secure_models import UnsignedEnvelope, SignedEnvelope
from .protocol.secure import PublicKey
from .protocol.api_models import EventsPayload
from .protocol.event import EventType
from .protocol.node import NodeProfile
from .network_graph import NetworkGraph
from .utils import sha256_hash


class Secure:
    identity: NodeIdentity
    graph: NetworkGraph
    
    def __init__(self, identity: NodeIdentity, graph: NetworkGraph):
        self.identity = identity
        self.graph = graph
        
    def create_envelope(self, payload, target) -> SignedEnvelope:
        return UnsignedEnvelope(
            payload=payload,
            source_node=self.identity.rid,
            target_node=target
        ).sign_with(self.identity.priv_key)
        
    def validate_envelope(self, envelope: SignedEnvelope):
        node_profile = self.graph.get_node_profile(
            envelope.source_node)
        
        if node_profile:
            pub_key = PublicKey.from_der(node_profile.public_key)
            envelope.verify_with(pub_key)
                            
            if envelope.target_node != self.identity.rid:
                raise Exception("I am not the target")
        
        else:
            # check if its a broadcast
            
            print(type(envelope.payload), envelope.payload)
            
            if type(envelope.payload) != EventsPayload:
                raise Exception("Unknown Node RID")
                 
            handshake_case = False
            
            for event in envelope.payload.events:
                if event.rid != envelope.source_node:
                    continue
                if event.event_type != EventType.NEW:
                    continue
                
                node_profile = event.bundle.validate_contents(NodeProfile)
                hashed_pub_key = sha256_hash(node_profile.public_key)

                if envelope.source_node.uuid != hashed_pub_key:
                    raise Exception("Invalid public key on new node!")
                
                handshake_case = True
                break
            
            if not handshake_case:
                raise Exception("Unknown Node RID")            

