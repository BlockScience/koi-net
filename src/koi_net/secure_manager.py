import structlog
import cryptography.exceptions
from rid_lib.ext import Bundle, Cache
from rid_lib.ext.utils import sha256_hash
from rid_lib.types import KoiNetNode
from .identity import NodeIdentity
from .protocol.envelope import UnsignedEnvelope, SignedEnvelope
from .protocol.secure import PublicKey
from .protocol.api_models import ApiModels, EventsPayload
from .protocol.event import EventType
from .protocol.node import NodeProfile
from .protocol.secure import PrivateKey
from .exceptions import (
    UnknownNodeError,
    InvalidKeyError,
    InvalidSignatureError,
    InvalidTargetError
)
from .config.base import BaseNodeConfig

log = structlog.stdlib.get_logger()


class SecureManager:
    """Subsystem handling secure protocol logic."""
    identity: NodeIdentity
    cache: Cache
    config: BaseNodeConfig
    priv_key: PrivateKey
    
    def __init__(
        self, 
        identity: NodeIdentity, 
        cache: Cache,
        config: BaseNodeConfig
    ):
        self.identity = identity
        self.cache = cache
        self.config = config
        
    def start(self):
        self.load_priv_key()
        
    def load_priv_key(self) -> PrivateKey:
        """Loads private key from PEM file path in config."""
        
        # TODO: handle missing private key
        with open(self.config.koi_net.private_key_pem_path, "r") as f:
            priv_key_pem = f.read()
        
        self.priv_key = PrivateKey.from_pem(
            priv_key_pem=priv_key_pem,
            password=self.config.env.priv_key_password
        )
        
    def handle_unknown_node(self, envelope: SignedEnvelope) -> Bundle | None:
        """Attempts to find node profile in proided envelope.
        
        If an unknown node sends an envelope, it may still be able to be
        validated if that envelope contains their node profile. This is
        essential for allowing unknown nodes to handshake and introduce
        themselves. Only an `EventsPayload` contain a `NEW` event for a 
        node profile for the source node is permissible.
        """
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
        
    def create_envelope(
        self, payload: ApiModels, target: KoiNetNode
    ) -> SignedEnvelope:
        """Returns signed envelope to target from provided payload."""
        return UnsignedEnvelope(
            payload=payload,
            source_node=self.identity.rid,
            target_node=target
        ).sign_with(self.priv_key)
        
    def validate_envelope(self, envelope: SignedEnvelope):
        """Validates signed envelope from another node."""
        
        node_bundle = (
            self.cache.read(envelope.source_node) or
            self.handle_unknown_node(envelope)
        )
        
        if not node_bundle:
            raise UnknownNodeError(f"Couldn't resolve {envelope.source_node}")
        
        node_profile = node_bundle.validate_contents(NodeProfile)
        
        # check that public key matches source node RID
        if envelope.source_node.hash != sha256_hash(node_profile.public_key):
            raise InvalidKeyError("Invalid public key on new node!")
        
        # check envelope signed by validated public key
        pub_key = PublicKey.from_der(node_profile.public_key)
        try:
            envelope.verify_with(pub_key)
        except cryptography.exceptions.InvalidSignature:
            raise InvalidSignatureError(f"Signature {envelope.signature} is invalid.")
        
        # check that this node is the target of the envelope
        if envelope.target_node != self.identity.rid:
            raise InvalidTargetError(f"Envelope target {envelope.target_node!r} is not me")

