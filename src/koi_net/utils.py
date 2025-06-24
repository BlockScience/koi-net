from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import hashlib


def generate_key_pair() -> tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]:
    priv_key = ec.generate_private_key(ec.SECP192R1())
    pub_key = priv_key.public_key()
    
    return priv_key, pub_key

def save_priv_key_to_pem(priv_key: ec.EllipticCurvePrivateKey) -> str:
    return priv_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()

def save_pub_key_to_pem(pub_key: ec.EllipticCurvePublicKey) -> str:
    return pub_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    
def load_priv_key_from_pem(priv_key_pem: str) -> ec.EllipticCurvePrivateKey:
    return serialization.load_pem_private_key(
        data=priv_key_pem.encode(),
        password=None
    )
    
def load_pub_key_from_pem(pub_key_pem: str) -> ec.EllipticCurvePublicKey:
    return serialization.load_pem_public_key(
        data=pub_key_pem.encode()
    )

def sha256_hash(data: str) -> str:
    hash = hashlib.sha256()
    hash.update(data.encode())
    return hash.hexdigest()