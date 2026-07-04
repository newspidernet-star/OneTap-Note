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


def get_secret(db, key: str) -> str | None:
    """读取一个 API key/凭证：环境变量 SMART_SCRIBE_<KEY_UPPER> 优先，其次 AES 加密的 DB 行。

    这样 Fly 等平台可用 secrets 注入 key（不落库、不入设置页）；本地仍可用设置页。
    """
    env_name = f"SMART_SCRIBE_{key.upper()}"
    val = os.environ.get(env_name)
    if val:
        return val
    from app.models import ApiSettings  # 延迟导入避免循环
    record = db.query(ApiSettings).filter_by(key=key).first()
    if record and record.encrypted_value:
        return decrypt(record.encrypted_value)
    return None