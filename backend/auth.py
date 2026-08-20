"""
Auth foundation — Prompt 0 stub.

Real authentication (JWT signup/login) is a later stage. For now this module
establishes the single, non-negotiable rule the whole architecture depends on:

    user_id is ALWAYS derived server-side and NEVER accepted from the client.

`get_current_user_id` is the one dependency every scoped endpoint will use.
It currently resolves a fixed stub identity so the isolation pattern is wired
from day one; swapping in JWT/session verification later changes only this
function, not the call sites.
"""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Stub identity used until real auth lands. Not client-controllable.
STUB_USER_ID = "000000000000000000000000"

# auto_error=False so the stub works without a token during Prompt 0.
_bearer = HTTPBearer(auto_error=False)


async def get_current_user_id(
    _credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """
    Return the authenticated user's id.

    Prompt 0: returns a fixed stub id. The client can never supply or override
    this value — that guarantee is the point of routing every query through
    this dependency.
    """
    return STUB_USER_ID
