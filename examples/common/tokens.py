"""A signed identity token — the demo's stand-in for an identity provider (Auth0 in the reference
diagram), stdlib only.

WHAT IT PROVES AND WHAT IT DOES NOT. It proves the one property the architecture needs: the role and
the tenant a request is served under come from a token the model never writes and cannot change —
not from the prompt, not from the model id. It is HS256 with a demo secret; a real deployment
verifies the provider's RS256 signature against its JWKS and maps its claims the same way
(`to_claim`). That verification is NOT built here and is said so wherever this is used.

    token = issue("cfo-north", "cfo", "northgate")          # what a sign-in hands a client
    claim = verify(token)                                      # what the gateway trusts, and nothing else
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from .permissions import Claim

DEMO_SECRET = b"lora-kernel-demo-only-not-a-secret"


class InvalidToken(PermissionError):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def issue(user_id: str, role: str, org_id: str, ttl: int = 3600, secret: bytes = DEMO_SECRET) -> str:
    head = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = _b64(json.dumps({"sub": user_id, "role": role, "org": org_id, "exp": int(time.time()) + ttl}).encode())
    sig = _b64(hmac.new(secret, f"{head}.{body}".encode(), hashlib.sha256).digest())
    return f"{head}.{body}.{sig}"


def verify(token: str, secret: bytes = DEMO_SECRET) -> Claim:
    try:
        head, body, sig = token.split(".")
    except ValueError:
        raise InvalidToken("not a signed token") from None
    want = _b64(hmac.new(secret, f"{head}.{body}".encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, want):
        raise InvalidToken("bad signature")
    claims = json.loads(_unb64(body))
    if claims.get("exp", 0) < time.time():
        raise InvalidToken("expired")
    return to_claim(claims)


def to_claim(claims: dict) -> Claim:
    """Provider claims → the tool layer's Claim. The one mapping a real provider would also need."""
    return Claim(user_id=claims["sub"], role=claims["role"], org_id=claims["org"])
