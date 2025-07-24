from typing import Generic, TypeVar
from pydantic import BaseModel, model_validator
from rid_lib.types import KoiNetNode

from .secure import PrivateKey, PublicKey
from .api_models import RequestModels, ResponseModels

T = TypeVar("T", bound=RequestModels | ResponseModels)


class SignedEnvelope(BaseModel, Generic[T]):
    payload: T
    source_node: KoiNetNode
    target_node: KoiNetNode
    signature: str
    
    @model_validator(mode="after")
    def verify_signature(self):
        ...
        
    
    def verify_with(self, pub_key: PublicKey) -> bool:
        unsigned_envelope = UnsignedEnvelope(
            **self.model_dump(exclude={"signature"})
        )
        
        return pub_key.verify(
            self.signature,
            unsigned_envelope.model_dump_json().encode()
        )

class UnsignedEnvelope(BaseModel, Generic[T]):
    payload: T
    source_node: KoiNetNode
    target_node: KoiNetNode
    
    def sign_with(self, priv_key: PrivateKey) -> SignedEnvelope:
        signature = priv_key.sign(
            self.model_dump_json().encode()
        )
        
        return SignedEnvelope(
            **self.model_dump(),
            signature=signature
        )
