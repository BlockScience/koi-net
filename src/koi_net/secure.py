from rid_lib.types import KoiNetNode
from rid_lib.ext import Bundle, Cache
from .identity import NodeIdentity
from .protocol.secure_models import UnsignedEnvelope, SignedEnvelope
from .protocol.secure import PublicKey
from .protocol.api_models import EventsPayload
from .protocol.event import EventType
from .protocol.node import NodeProfile
from .utils import sha256_hash


class Secure:
    identity: NodeIdentity
    cache: Cache
    
    def __init__(self, identity: NodeIdentity, cache: Cache):
        self.identity = identity
        self.cache = cache
        
    # def validate_profile_bundle(self, bundle: Bundle[NodeProfile]):
    #     if type(bundle.rid) != KoiNetNode:
    #         raise Exception("Not a node profile")
                
    #     node_profile = bundle.validate_contents(NodeProfile)
        
        
    def create_envelope(self, payload, target) -> SignedEnvelope:
        return UnsignedEnvelope(
            payload=payload,
            source_node=self.identity.rid,
            target_node=target
        ).sign_with(self.identity.priv_key)
        
    def validate_envelope(self, envelope: SignedEnvelope):
        # NOTE: can be replaced by deref
        node_bundle = self.cache.read(envelope.source_node)
        
        if node_bundle:
            node_profile = node_bundle.validate_contents(NodeProfile)
            pub_key = PublicKey.from_der(node_profile.public_key)
            envelope.verify_with(pub_key)
                            
            if envelope.target_node != self.identity.rid:
                raise Exception("I am not the target")
        
        else:            
            if type(envelope.payload) != EventsPayload:
                raise Exception("Unknown Node RID")
                 
            found_profile = False
            for event in envelope.payload.events:
                if event.rid != envelope.source_node:
                    continue
                if event.event_type != EventType.NEW:
                    continue
                
                node_profile = event.bundle.validate_contents(NodeProfile)
                hashed_pub_key = sha256_hash(node_profile.public_key)

                if envelope.source_node.uuid != hashed_pub_key:
                    raise Exception("Invalid public key on new node!")
                
                found_profile = True
                break
            
            if not found_profile:
                raise Exception("Unknown Node RID")            

