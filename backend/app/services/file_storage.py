"""Encrypted-at-rest storage for uploaded policy PDFs (Fernet, key from settings.FILE_ENCRYPTION_KEY)."""

import uuid
from pathlib import Path

from cryptography.fernet import Fernet

from app.config import settings

_STORAGE_ROOT = Path(__file__).resolve().parent.parent.parent / "storage" / "policies"
_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(settings.FILE_ENCRYPTION_KEY.encode())
    return _fernet


def save_encrypted_pdf(raw_bytes: bytes) -> str:
    """Encrypts raw_bytes and writes it to disk. Returns the path, relative to backend/, as a string."""
    _STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4()}.pdf.enc"
    path = _STORAGE_ROOT / filename
    path.write_bytes(_get_fernet().encrypt(raw_bytes))
    return str(path.relative_to(_STORAGE_ROOT.parent.parent))


def read_decrypted_pdf(relative_path: str) -> bytes:
    path = _STORAGE_ROOT.parent.parent / relative_path
    return _get_fernet().decrypt(path.read_bytes())
