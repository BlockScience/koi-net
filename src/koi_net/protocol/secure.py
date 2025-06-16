from base64 import urlsafe_b64decode, urlsafe_b64encode
import cryptography
import cryptography.exceptions
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization


class PrivateKey:
    priv_key: ec.EllipticCurvePrivateKey
    
    def __init__(self, priv_key):
        self.priv_key = priv_key
        
    @classmethod
    def generate(cls):
        return cls(priv_key=ec.generate_private_key(ec.SECP192R1()))
    
    @classmethod
    def from_pem(cls, priv_key_pem: str, password: str | None = None):
        return cls(
            priv_key=serialization.load_pem_private_key(
                data=priv_key_pem.encode(),
                password=password.encode()
            )
        )
    
    def public_key(self) -> "PublicKey":
        return PublicKey(self.priv_key.public_key())
    
    def to_pem(self, password: str | None = None) -> str:
        return self.priv_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(password.encode())
        ).decode()
        
    def sign(self, message: bytes) -> str:
        return urlsafe_b64encode(
            self.priv_key.sign(
                data=message,
                signature_algorithm=ec.ECDSA(hashes.SHA256())
            )
        ).decode()

class PublicKey:
    pub_key: ec.EllipticCurvePublicKey
    
    def __init__(self, pub_key):
        self.pub_key = pub_key
    
    @classmethod
    def from_pem(cls, pub_key_pem: str):
        return cls(
            pub_key=serialization.load_pem_public_key(
                data=pub_key_pem.encode()
            )
        )
        
    def to_pem(self) -> str:
        return self.pub_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        
    @classmethod
    def from_der(cls, pub_key_der: str):        
        return cls(
            pub_key=serialization.load_der_public_key(
                data=urlsafe_b64decode(pub_key_der)
            )
        )
    
    def to_der(self) -> str:
        return urlsafe_b64encode(
            self.pub_key.public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        ).decode()
        
    def verify(self, signature: str, message: bytes) -> bool:
        try:
            self.pub_key.verify(
                signature=urlsafe_b64decode(signature),
                data=message,
                signature_algorithm=ec.ECDSA(hashes.SHA256())
            )
            return True
        except cryptography.exceptions.InvalidSignature:
            return False