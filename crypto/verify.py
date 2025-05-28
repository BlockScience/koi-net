import cryptography
import cryptography.exceptions
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from base64 import urlsafe_b64decode
import json

try:
    with open("public_key.pem", "r") as f:
        public_key_pem = f.read().encode()
    public_key = serialization.load_pem_public_key(public_key_pem)
    print("Loaded public key from disk")
    
except FileNotFoundError:
    print("Public key not found")
    quit()
    
try:
    with open("signature.json", "r") as f:
        sig_obj = json.load(f)

except (FileNotFoundError, json.JSONDecodeError):
    print("Signature file not found")
    quit()

signature = urlsafe_b64decode(sig_obj["signature"].encode())
message = sig_obj["message"].encode()

try:
    public_key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
    print("Valid signature")
except cryptography.exceptions.InvalidSignature:
    print("Invalid signature")