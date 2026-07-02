import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings


def ensure_secret_key() -> bytes:
    settings = get_settings()
    key_file = settings.secret_key_file
    key_file.parent.mkdir(parents=True, exist_ok=True)
    if not key_file.exists():
        key = AESGCM.generate_key(bit_length=256)
        key_file.write_bytes(key)
        key_file.chmod(0o600)
        return key
    return key_file.read_bytes()


def encrypt(plaintext: str) -> str:
    key = ensure_secret_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()


def decrypt(ciphertext: str) -> str:
    key = ensure_secret_key()
    raw = base64.b64decode(ciphertext)
    nonce, ct = raw[:12], raw[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, None).decode()