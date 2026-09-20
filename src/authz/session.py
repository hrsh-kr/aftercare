"""Who is signed in -- decided by the server, never by the client.

The old dashboard sent `X-Staff-Brand` from sessionStorage, so Cedar was authorizing a
claim the browser made about itself. Now staff sign in with a passcode (PBKDF2-hashed in
fixtures/staff.json), the server issues a signed, expiring, HttpOnly cookie, and the
Cedar principal is built from that cookie only. Demo scale: a fixture instead of a user
pool -- in production this is Amazon Cognito issuing the token, with Verified Permissions
(managed Cedar) making the decision.
"""

import hashlib
import hmac
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from itsdangerous import BadSignature, URLSafeTimedSerializer

STAFF_FILE = Path(__file__).resolve().parent.parent.parent / "fixtures" / "staff.json"
COOKIE = "aftercare_session"
MAX_AGE = 8 * 3600
_ITER = 100_000
_serializer = URLSafeTimedSerializer(os.environ.get("AFTERCARE_SECRET", "aftercare-dev-secret-change-me"), salt="aftercare-session")


@dataclass
class Principal:
    username: str
    name: str
    brand: str
    role: str  # "manager" | "agent"


def hash_passcode(passcode: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", passcode.encode(), bytes.fromhex(salt), _ITER).hex()


def staff_directory() -> list[dict]:
    """Public part of each staff record (no hashes) -- what the login page lists."""
    return [{k: s[k] for k in ("username", "name", "brand", "role")} for s in json.loads(STAFF_FILE.read_text())]


def authenticate(username: str, passcode: str) -> Principal | None:
    for s in json.loads(STAFF_FILE.read_text()):
        if s["username"] == username:
            if hmac.compare_digest(hash_passcode(passcode, s["salt"]), s["hash"]):
                return Principal(s["username"], s["name"], s["brand"], s["role"])
            return None
    hash_passcode(passcode, "00" * 16)  # same work whether or not the user exists
    return None


def issue(p: Principal) -> str:
    return _serializer.dumps(asdict(p))


def verify(token: str | None) -> Principal | None:
    if not token:
        return None
    try:
        return Principal(**_serializer.loads(token, max_age=MAX_AGE))
    except (BadSignature, TypeError):
        return None
