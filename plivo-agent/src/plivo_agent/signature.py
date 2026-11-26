"""Tells a request that Plivo sent from one a stranger sent, using Plivo's V3 signature."""

import base64
import hashlib
import hmac
from collections.abc import Iterable, Mapping

Fields = Iterable[tuple[str, str]]


def is_from_plivo(
    auth_token: str, urls: Iterable[str], headers: Mapping[str, str], query: Fields = (), form: Fields = ()
) -> bool:
    """True when a signature on the request matches one of the addresses Plivo may have signed."""
    nonce = headers.get("x-plivo-signature-v3-nonce", "")
    # A subaccount's request is signed with its own token and, in the second header, the main account's.
    sent = f"{headers.get('x-plivo-signature-v3', '')},{headers.get('x-plivo-signature-ma-v3', '')}".split(",")
    expected = [sign(auth_token, url, nonce, query, form) for url in urls]
    return bool(nonce) and any(hmac.compare_digest(ours, theirs.strip()) for ours in expected for theirs in sent)


def sign(auth_token: str, url: str, nonce: str, query: Fields = (), form: Fields = ()) -> str:
    """Plivo's V3 signature: the address, its sorted query, the sorted form fields, then the nonce."""
    asked = "&".join(f"{name}={value}" for name, value in sorted(query))
    posted = "".join(name + value for name, value in sorted(form))
    fields = ("?" if asked or posted else "") + asked + ("." if asked and posted else "") + posted
    digest = hmac.new(auth_token.encode(), f"{url}{fields}.{nonce}".encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()
