from .identity import NodeIdentity
from .protocol.secure_models import UnsignedEnvelope, SignedEnvelope


class Secure:
    identity: NodeIdentity
    
    def __init__(self, identity: NodeIdentity):
        self.identity = identity
        
    def create_envelope(self, payload, target) -> SignedEnvelope:
        return UnsignedEnvelope(
            payload=payload,
            source_node=self.identity.rid,
            target_node=target
        ).sign_with(self.identity.priv_key)
