import logging
from typing import Generic, TypeVar
from pydantic import BaseModel
from rid_lib.types import KoiNetNode

from .secure import PrivateKey, PublicKey
from .api_models import RequestModels, ResponseModels


logger = logging.getLogger(__name__)


T = TypeVar("T", bound=RequestModels | ResponseModels)

class SignedEnvelope(BaseModel, Generic[T]):
    payload: T
    source_node: KoiNetNode
    target_node: KoiNetNode
    signature: str
    
    def verify_with(self, pub_key: PublicKey):        
        # IMPORTANT: calling `model_dump()` loses all typing! when converting between SignedEnvelope and UnsignedEnvelope, use the Pydantic classes, not the dictionary form
        unsigned_envelope = UnsignedEnvelope[T](
            payload=self.payload,
            source_node=self.source_node,
            target_node=self.target_node 
        )
        
        logger.debug(f"Verifying envelope: {unsigned_envelope.model_dump_json()}")
        
        pub_key.verify(
            self.signature,
            unsigned_envelope.model_dump_json().encode()
        )

class UnsignedEnvelope(BaseModel, Generic[T]):
    payload: T
    source_node: KoiNetNode
    target_node: KoiNetNode
    
    def sign_with(self, priv_key: PrivateKey) -> SignedEnvelope[T]:
        logger.debug(f"Signing envelope: {self.model_dump_json()}")
        logger.debug(f"Type: [{type(self.payload)}]")
        
        signature = priv_key.sign(
            self.model_dump_json().encode()
        )
        
        return SignedEnvelope(
            payload=self.payload,
            source_node=self.source_node,
            target_node=self.target_node,
            signature=signature
        )
