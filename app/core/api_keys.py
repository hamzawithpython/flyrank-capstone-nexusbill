import hashlib
import secrets

def generate_api_key() -> tuple[str, str, str]:
    """Returns (full_key, key_prefix, key_hash). full_key is shown to the
    caller exactly once; only key_hash is ever persisted."""
    secret = secrets.token_urlsafe(32)
    full_key = f"nb_live_{secret}"
    key_prefix = full_key[:12]
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, key_prefix, key_hash