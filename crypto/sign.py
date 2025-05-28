from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from base64 import urlsafe_b64encode
import json

try:
    with open("private_key.pem", "r") as f:
        private_key_pem = f.read().encode()
    private_key = serialization.load_pem_private_key(private_key_pem, password=None)
    print("Loaded private key from disk")

except FileNotFoundError:
    private_key = ec.generate_private_key(ec.SECP192R1())
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()
    
    with open("private_key.pem", "w") as f:
        f.write(private_key_pem)
        
    print("Genreated new private key")

public_key = private_key.public_key()

public_key_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode()

with open("public_key.pem", "w") as f:
    f.write(public_key_pem)

message = input("Message to sign:\n> ").encode()

signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))

with open("signature.json", "w") as f:
    signature_b64 = urlsafe_b64encode(signature)
    json.dump({
        "message": message.decode(),
        "signature": signature_b64.decode()
    }, f)

    print(signature_b64)