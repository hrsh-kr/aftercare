"""Authorization, decided by the real Cedar evaluator.

Aftercare is one backend serving several independent brands. Which brand's data a person
may see -- and what they may change -- is decided by Cedar policies (policies/aftercare.cedar,
checked against policies/aftercare.cedarschema), not by an `if principal == resource` in
Python. If Cedar denies, or can't be reached at all, this denies too: fails closed.

Each decision returns the ids of the policies that decided it, so the UI can say *why*.

The `cedar-policy` package on PyPI is an empty reserved placeholder (0.0.1, no bindings),
so this uses the open-source CLI (scripts/install_cedar_cli.sh). In production the same
policies and schema load unchanged into Amazon Verified Permissions.
"""

import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
# Overridable so the SAM Local package can point at the linux/aarch64 binary it bundles.
CEDAR_BIN = Path(os.environ.get("CEDAR_BIN", str(ROOT / "tools" / "cedar" / "cedar")))
POLICY_PATH = ROOT / "policies" / "aftercare.cedar"
SCHEMA_PATH = ROOT / "policies" / "aftercare.cedarschema"


class CedarUnavailable(RuntimeError):
    pass


@dataclass
class Decision:
    allowed: bool
    policies: list[str] = field(default_factory=list)  # @id of each policy that decided it


def _run(args: list[str]) -> subprocess.CompletedProcess:
    if not CEDAR_BIN.exists():
        raise CedarUnavailable(f"Cedar CLI not found at {CEDAR_BIN} -- run scripts/install_cedar_cli.sh")
    try:
        return subprocess.run([str(CEDAR_BIN), *args], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CedarUnavailable(f"Cedar CLI call failed: {exc}") from exc


def validate() -> tuple[bool, str]:
    """`cedar validate`: do the policies type-check against the schema?"""
    r = _run(["validate", "--schema", str(SCHEMA_PATH), "--policies", str(POLICY_PATH)])
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def authorize(principal: dict, action: str, resource_type: str, resource_id: str, resource_attrs: dict) -> Decision:
    """principal = {"id", "brand", "role"} as established by the server (session.py)."""
    entities = [
        {"uid": {"type": "Staff", "id": principal["id"]}, "attrs": {"brand": principal["brand"], "role": principal["role"]}, "parents": []},
        {"uid": {"type": resource_type, "id": resource_id}, "attrs": resource_attrs, "parents": []},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(entities, f)
        path = f.name
    try:
        r = _run([
            "authorize", "--verbose", "--schema", str(SCHEMA_PATH), "--policies", str(POLICY_PATH), "--entities", path,
            "--principal", f'Staff::"{principal["id"]}"', "--action", f'Action::"{action}"',
            "--resource", f'{resource_type}::"{resource_id}"',
        ])
    finally:
        Path(path).unlink(missing_ok=True)

    # Exit codes: 0 = ALLOW, 2 = DENY, anything else = a request/policy error. Only 0 grants,
    # so an error message that happens to contain "ALLOW" can never be misread as a grant.
    if r.returncode not in (0, 2):
        raise CedarUnavailable(f"Cedar error: {(r.stderr or r.stdout).strip()[:200]}")
    m = re.search(r"policies:\n((?:\s+\S+\n?)+)", r.stdout)
    return Decision(allowed=r.returncode == 0, policies=m.group(1).split() if m else [])


def can_view_dashboard(principal: dict, brand: str) -> Decision:
    return authorize(principal, "viewDashboard", "Brand", brand, {"brand": brand})
