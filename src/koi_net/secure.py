from rid_lib.ext import Bundle
from .identity import NodeIdentity
from .protocol.secure_models import UnsignedEnvelope, SignedEnvelope
from .protocol.secure import PublicKey
from .protocol.api_models import EventsPayload
from .protocol.event import EventType
from .protocol.node import NodeProfile
from .utils import sha256_hash
from .effector import Effector


class Secure:
    identity: NodeIdentity
    effector: Effector
    
    def __init__(self, identity: NodeIdentity, effector: Effector):
        self.identity = identity
        self.effector = effector
    
    def _handle_unknown_node(self, envelope: SignedEnvelope) -> Bundle | None:
        if type(envelope.payload) != EventsPayload:
            return None
            
        for event in envelope.payload.events:
            # must be NEW event for bundle of source node's profile
            if event.rid != envelope.source_node:
                continue
            if event.event_type != EventType.NEW:
                continue            
            
            return event.bundle
        return None
        
    def create_envelope(self, payload, target) -> SignedEnvelope:
        return UnsignedEnvelope(
            payload=payload,
            source_node=self.identity.rid,
            target_node=target
        ).sign_with(self.identity.priv_key)
        
    def validate_envelope(self, envelope: SignedEnvelope):
        node_bundle = (
            self.effector.deref(envelope.source_node) or
            self._handle_unknown_node(envelope)
        )
        
        if not node_bundle:
            raise Exception("Unknown node")
        
        node_profile = node_bundle.validate_contents(NodeProfile)
        
        # check that public key matches source node RID
        hashed_pub_key = sha256_hash(node_profile.public_key)
        if envelope.source_node.uuid != hashed_pub_key:
            raise Exception("Invalid public key on new node!")
        
        # check envelope signed by validated public key
        pub_key = PublicKey.from_der(node_profile.public_key)
        envelope.verify_with(pub_key)
        
        # check that this node is the target of the envelope
        if envelope.target_node != self.identity.rid:
            raise Exception("I am not the target")

