"""
Credential Vault
----------------
민감 자격증명(SSH Key, 비밀번호, API Key)을 암호화하여 vault.db에 저장한다.

암호화: Fernet (AES-128-CBC + HMAC-SHA256)
마스터 키: OS Keychain(keyring) 우선, 없으면 vault.db 옆 .key 파일에 저장.
"""

import base64
import os
from pathlib import Path

from cryptography.fernet import Fernet

from aidevops.config import settings

_KEY_FILE = settings.data_dir / ".vault_key"


def _load_or_create_master_key() -> bytes:
    """마스터 키를 로드하거나 신규 생성한다."""
    # 1) OS Keychain 시도
    try:
        import keyring
        stored = keyring.get_password("aidevops", "vault_master_key")
        if stored:
            return base64.urlsafe_b64decode(stored.encode())
    except Exception:
        pass

    # 2) 파일 fallback
    if _KEY_FILE.exists():
        return base64.urlsafe_b64decode(_KEY_FILE.read_bytes())

    # 3) 신규 생성
    key = Fernet.generate_key()
    settings.ensure_data_dir()
    _KEY_FILE.write_bytes(base64.urlsafe_b64encode(key))
    _KEY_FILE.chmod(0o600)

    try:
        import keyring
        keyring.set_password("aidevops", "vault_master_key", base64.urlsafe_b64encode(key).decode())
    except Exception:
        pass

    return key


def _get_fernet() -> Fernet:
    return Fernet(_load_or_create_master_key())


def encrypt(plaintext: str) -> str:
    """평문 문자열을 암호화하여 base64 문자열로 반환한다."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """암호화된 base64 문자열을 복호화하여 평문으로 반환한다."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()
