import os
import base64
from itertools import cycle

def _get_key():
    # Simple key derivation from env or default
    secret = os.getenv("GEMINI_API_KEY", "hirelink-default-secret-key-change-me")
    if not secret: secret = "fallback-key"
    return secret

def xor_cipher(text: str, key: str) -> str:
    return ''.join(chr(ord(c) ^ ord(k)) for c, k in zip(text, cycle(key)))

def encrypt_value(value: str) -> str:
    """Encrypts a string value using simple XOR + Base64."""
    if not value: return ""
    try:
        key = _get_key()
        xor_text = xor_cipher(value, key)
        # return base64 encoded string
        return base64.urlsafe_b64encode(xor_text.encode("utf-8")).decode("utf-8")
    except Exception as e:
        print(f"Encryption failed: {e}")
        return value

def decrypt_value(token: str) -> str:
    """Decrypts a string token."""
    if not token or not isinstance(token, str): return ""
    try:
        key = _get_key()
        # decode base64
        xor_text_bytes = base64.urlsafe_b64decode(token.encode("utf-8"))
        xor_text = xor_text_bytes.decode("utf-8")
        return xor_cipher(xor_text, key)
    except Exception:
         # Fallback for legacy plain text
        return token
