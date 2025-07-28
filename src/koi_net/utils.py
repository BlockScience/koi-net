import hashlib


def sha256_hash(data: str) -> str:
    hash = hashlib.sha256()
    hash.update(data.encode())
    return hash.hexdigest()