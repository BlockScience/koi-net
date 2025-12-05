import structlog
from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict
from rid_lib.types import KoiNetNode

from .secure import PrivateKey, PublicKey
from .api_models import RequestModels, ResponseModels

log = structlog.stdlib.get_logger()


T = TypeVar("T", bound=RequestModels | ResponseModels)

class SignedEnvelope(BaseModel, Generic[T]):
    payload: T
    source_node: KoiNetNode
    target_node: KoiNetNode
    signature: str
    
    model_config = ConfigDict(exclude_none=True)
    
    def verify_with(self, pub_key: PublicKey):
        """Verifies signed envelope with public key.
        
        Raises `cryptography.exceptions.InvalidSignature` on failure.
        """
        
        # IMPORTANT: calling `model_dump()` loses all typing! when converting between SignedEnvelope and UnsignedEnvelope, use the Pydantic classes, not the dictionary form
        
        unsigned_envelope = UnsignedEnvelope[T](
            payload=self.payload,
            source_node=self.source_node,
            target_node=self.target_node 
        )
        
        log.debug(f"Verifying envelope: {unsigned_envelope.model_dump_json(exclude_none=True)}")

        pub_key.verify(
            self.signature,
            unsigned_envelope.model_dump_json(exclude_none=True).encode()
        )

class UnsignedEnvelope(BaseModel, Generic[T]):
    payload: T
    source_node: KoiNetNode
    target_node: KoiNetNode
    
    model_config = ConfigDict(exclude_none=True)
    
    def sign_with(self, priv_key: PrivateKey) -> SignedEnvelope[T]:
        """Signs with private key and returns `SignedEnvelope`."""
        
        log.debug(f"Signing envelope: {self.model_dump_json(exclude_none=True)}")
        log.debug(f"Type: [{type(self.payload)}]")
        
        signature = priv_key.sign(
            self.model_dump_json(exclude_none=True).encode()
        )
        
        return SignedEnvelope(
            payload=self.payload,
            source_node=self.source_node,
            target_node=self.target_node,
            signature=signature
        )
