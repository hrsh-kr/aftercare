"""Brand-scoped dashboard authorization, backed by the real Cedar CLI.

Aftercare is one backend serving several independent brands. A brand's
dashboard must never leak another brand's tickets. That boundary is
enforced here by shelling out to Cedar's own evaluator against
policies/dashboard.cedar -- not by an `if principal == resource` check
written in Python. If Cedar denies it, or can't be reached at all, this
denies too: fails closed, same honesty rule as the rest of the system
(see DESIGN.md section 7) -- never let a broken dependency silently grant
access it shouldn't.

The `cedar-policy` package on PyPI is an empty reserved placeholder (0.0.1,
no actual bindings) -- this uses the real open-source CLI instead. See
scripts/install_cedar_cli.sh.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
# Overridable so the SAM Local Lambda package can point at the
# linux/aarch64 binary it bundles (tools/cedar-lambda/cedar) instead of
# the host-native one Flask uses -- a macOS binary can't execute inside
# that container. See scripts/install_cedar_cli.sh.
CEDAR_BIN = Path(os.environ.get("CEDAR_BIN", str(ROOT / "tools" / "cedar" / "cedar")))
POLICY_PATH = ROOT / "policies" / "dashboard.cedar"

KNOWN_BRANDS = ["arcticair", "aquaspin"]


class CedarUnavailable(RuntimeError):
    pass


def _entities() -> list[dict]:
    entities = []
    for brand in KNOWN_BRANDS:
        entities.append({"uid": {"type": "Staff", "id": brand}, "attrs": {"brand": brand}, "parents": []})
        entities.append({"uid": {"type": "Brand", "id": brand}, "attrs": {"brand": brand}, "parents": []})
    return entities


def can_view_dashboard(staff_brand: str, requested_brand: str) -> bool:
    """Is the staff member logged in as `staff_brand` allowed to view
    `requested_brand`'s dashboard? Runs the real Cedar CLI; raises
    CedarUnavailable rather than guessing if it can't."""
    if not CEDAR_BIN.exists():
        raise CedarUnavailable(f"Cedar CLI not found at {CEDAR_BIN} -- run scripts/install_cedar_cli.sh")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(_entities(), f)
        entities_path = f.name

    try:
        result = subprocess.run(
            [
                str(CEDAR_BIN), "authorize",
                "--policies", str(POLICY_PATH),
                "--entities", entities_path,
                "--principal", f'Staff::"{staff_brand}"',
                "--action", 'Action::"viewDashboard"',
                "--resource", f'Brand::"{requested_brand}"',
            ],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CedarUnavailable(f"Cedar CLI call failed: {exc}") from exc
    finally:
        Path(entities_path).unlink(missing_ok=True)

    return "ALLOW" in result.stdout
