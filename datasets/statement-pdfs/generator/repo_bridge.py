"""Stand-ins for the source system's helpers used by the generators.

``issuer_encryption`` is a fictional AES-256 profile for Bank Z (empty user
password, random owner password); it is not any real issuer's profile.
"""

from io import BytesIO
from types import SimpleNamespace

import pikepdf


def issuer_encryption() -> pikepdf.Encryption:
    """Return Bank Z's fictional encryption profile."""
    return pikepdf.Encryption(owner="bank-z-owner", user="", R=6,
                              allow=pikepdf.Permissions(modify_other=False, modify_annotation=False))


def set_profile_permissions(pdf: bytes) -> bytes:
    """No-op: the fictional profile needs no post-processing."""
    return pdf


def _decrypt_pdf(pdf: bytes, password: str) -> bytes:
    """Open with the password and save unencrypted, keeping the Info dictionary."""
    out = BytesIO()
    with pikepdf.open(BytesIO(pdf), password=password) as p:
        p.save(out)
    return out.getvalue()


pu = SimpleNamespace(decrypt_pdf=_decrypt_pdf)
