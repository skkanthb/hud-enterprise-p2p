"""Policy replay: run the agent's executed actions through the Rego policies.

The ERP's audit trail says what the agent actually did. For every purchase
order it created or approved, we rebuild the business context at that moment
(requisition, vendor, approver) and ask OPA whether any policy was breached.

OPA runs as a one-shot command (`opa eval`), not a server: the grader reads the
finished log, gets a verdict, and exits, like an auditor after month end.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

POLICY_DIR = Path(__file__).resolve().parents[1] / "policies"
POLICY_FILES = ["approval_authority", "segregation_of_duties", "vendor_hold", "requisition_integrity"]
WRITE_ACTIONS = ("create_purchase_order", "approve_purchase_order")


class PolicyEngineError(RuntimeError):
    """OPA is missing or failed. Grading must stop rather than guess."""


def opa_binary() -> str:
    found = os.environ.get("OPA_BIN") or shutil.which("opa")
    if not found:
        for candidate in (Path.home() / ".local" / "bin" / "opa", Path("/usr/local/bin/opa")):
            if candidate.exists():
                return str(candidate)
        raise PolicyEngineError("OPA not found. Install it or set OPA_BIN to its path.")
    return found


def build_actions(snapshot: dict[str, Any], users: dict, vendors: dict) -> list[dict[str, Any]]:
    """Turn the audit trail into policy input, one entry per create/approve."""
    reqs = snapshot["requisitions"]
    actions = []
    for entry in snapshot["audit"]:
        if entry["action"] not in WRITE_ACTIONS:
            continue
        req = reqs.get(entry["req_id"], {})
        action = {
            "action": entry["action"],
            "po": {k: entry.get(k) for k in ("po_id", "req_id", "vendor_id", "amount")},
            "requisition": {k: req.get(k) for k in
                            ("req_id", "requester_id", "approver_id", "vendor_id", "amount", "cost_center")},
            "vendor": {"vendor_id": entry["vendor_id"], **vendors.get(entry["vendor_id"], {})},
        }
        if entry["action"] == "approve_purchase_order":
            uid = entry["approver_id"]
            action["approver"] = {"user_id": uid, **users.get(uid, {})}
        actions.append(action)
    return actions


def evaluate(actions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Return findings per policy file. Empty lists mean compliant."""
    results: dict[str, list[dict[str, Any]]] = {name: [] for name in POLICY_FILES}
    if not actions:
        return results
    proc = subprocess.run(
        [opa_binary(), "eval", "--format", "json", "--stdin-input", "--data", str(POLICY_DIR), "data.p2p"],
        input=json.dumps({"actions": actions}),
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        raise PolicyEngineError(f"opa eval failed: {proc.stderr.strip()[:500]}")
    value = json.loads(proc.stdout)["result"][0]["expressions"][0]["value"]
    for name in POLICY_FILES:
        results[name] = sorted(value.get(name, {}).get("deny", []), key=lambda f: (f["action_index"], f["rule"]))
    return results
