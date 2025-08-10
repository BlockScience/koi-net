import logging
from functools import wraps

import cryptography.exceptions
from rid_lib.ext import Bundle
from rid_lib.ext.utils import sha256_hash
from .identity import NodeIdentity
from .protocol.envelope import UnsignedEnvelope, SignedEnvelope
from .protocol.secure import PublicKey
from .protocol.api_models import EventsPayload
from .protocol.event import EventType
from .protocol.node import NodeProfile
from .protocol.secure import PrivateKey
from .protocol.errors import (
    UnknownNodeError,
    InvalidKeyError,
    InvalidSignatureError,
    InvalidTargetError
)
from .effector import Effector
from .config import NodeConfig

logger = logging.getLogger(__name__)


class Secure:
    identity: NodeIdentity
    effector: Effector
    config: NodeConfig
    priv_key: PrivateKey
    
    def __init__(
        self, 
        identity: NodeIdentity, 
        effector: Effector,
        config: NodeConfig
    ):
        self.identity = identity
        self.effector = effector
        self.config = config

        self.priv_key = self._load_priv_key()
        
    def _load_priv_key(self) -> PrivateKey:
        with open(self.config.koi_net.private_key_pem_path, "r") as f:
            priv_key_pem = f.read()
        
        return PrivateKey.from_pem(
            priv_key_pem=priv_key_pem,
            password=self.config.env.priv_key_password
        )
        
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
        ).sign_with(self.priv_key)
        
    def validate_envelope(self, envelope: SignedEnvelope):
        node_bundle = (
            self.effector.deref(envelope.source_node) or
            self._handle_unknown_node(envelope)
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
        except cryptography.exceptions.InvalidSignature as err:
            raise InvalidSignatureError(f"Signature {envelope.signature} is invalid.")
        
        # check that this node is the target of the envelope
        if envelope.target_node != self.identity.rid:
            raise InvalidTargetError(f"Envelope target {envelope.target_node!r} is not me")
        
    def envelope_handler(self, func):
        @wraps(func)
        async def wrapper(req: SignedEnvelope, *args, **kwargs) -> SignedEnvelope | None:
            logger.info("Validating envelope")
            
            self.validate_envelope(req)            
            logger.info("Calling endpoint handler")
            
            result = await func(req, *args, **kwargs)            
            
            if result is not None:
                logger.info("Creating response envelope")
                return self.create_envelope(
                    payload=result,
                    target=req.source_node
                )
        return wrapper

