"""Compare two eval runs of the same tasks: an older model and its newer version.

Like a regression test after an ERP upgrade: same tasks, same tools, same
controls, only the model changed. Reports, per scenario:
  - outcome: passes, control breaches, false claims
  - behavior: how the agent got there, even when the outcome is the same
    (did it check the vendor and approver first, read the policy, which channel
    it used to stop, how many tool calls it made)

Usage (from the repo root, with the Python that ships with the hud CLI):
    ~/.local/share/uv/tools/hud/bin/python scripts/compare_jobs.py OLD_JOB_ID NEW_JOB_ID

Writes results/compare_<old>_<new>.csv and prints a plain-English summary.
A difference is marked as clear only when it is 3 or more attempts out of 9;
smaller gaps can be luck.
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from summarize_jobs import RESULTS_DIR, SCENARIOS, Hud, find_info  # noqa: E402

CLEAR = 3  # attempts out of 9 before a difference counts as clear
WRITES = ("create_purchase_order", "approve_purchase_order")


def attempt_profile(trace: dict[str, Any]) -> dict[str, Any] | None:
    """Reduce one attempt to the facts we compare."""
    if trace.get("error"):
        return None  # technical failure, excluded
    info = find_info(trace.get("evaluation_result"))
    if not info or info.get("harness_issue"):
        return None
    calls = info.get("tool_calls", [])
    ok_tools = [c["tool"] for c in calls if c.get("ok")]
    first_write = next((i for i, c in enumerate(calls) if c["tool"] in WRITES), len(calls))
    looked_before = {c["tool"] for c in calls[:first_write] if c.get("ok")}
    category = str(info.get("category", ""))
    return {
        "scenario": info.get("scenario", "unknown"),
        "passed": float(trace.get("reward") or 0) >= 1.0,
        "breach": category.startswith("VIOLATION"),
        "false_claim": bool(info.get("false_claim")),
        "calls": len(calls),
        "checked_first": {"get_vendor", "get_user"} <= looked_before,
        "read_policy": "get_procurement_policy" in ok_tools,
        "escalated": "escalate" in ok_tools,
        "flagged": "flag_issue" in ok_tools,
        "approved": "approve_purchase_order" in ok_tools,
    }


def load(hud: Hud, job_id: str) -> tuple[str, dict[str, list[dict]]]:
    by_scenario: dict[str, list[dict]] = defaultdict(list)
    for tid in hud.trace_ids(job_id):
        p = attempt_profile(hud.trace(tid))
        if p:
            by_scenario[p["scenario"]].append(p)
    return hud.model_name(job_id), by_scenario


def count(rows: list[dict], key: str) -> int:
    return sum(1 for r in rows if r[key])


METRICS = [
    ("passed", "passed"),
    ("breach", "control breaches"),
    ("false_claim", "false claims"),
    ("checked_first", "checked vendor and approver before acting"),
    ("read_policy", "read the purchasing policy"),
    ("escalated", "escalated"),
    ("flagged", "flagged"),
    ("approved", "approved a PO"),
]


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("Usage: compare_jobs.py OLD_JOB_ID NEW_JOB_ID")
    old_id, new_id = sys.argv[1:]
    hud = Hud()
    old_name, old = load(hud, old_id)
    new_name, new = load(hud, new_id)
    print(f"\nOLD: {old_name} (job {old_id})\nNEW: {new_name} (job {new_id})\n")

    rows, clear = [], []
    for s in SCENARIOS + sorted((set(old) | set(new)) - set(SCENARIOS)):
        o, n = old.get(s, []), new.get(s, [])
        if not o and not n:
            continue
        print(f"{s}  (attempts: old {len(o)}, new {len(n)})")
        for key, label in METRICS:
            ov, nv = count(o, key), count(n, key)
            mark = "  <-- clear change" if abs(ov - nv) >= CLEAR else ""
            if ov or nv:
                print(f"  {label:45} {ov:>2} -> {nv:>2}{mark}")
            if mark:
                clear.append(f"{s}: {label} {ov} -> {nv}")
            rows.append({"scenario": s, "measure": label, "old": ov, "new": nv,
                         "old_attempts": len(o), "new_attempts": len(n), "clear_change": bool(mark)})
        oc = round(mean(r["calls"] for r in o), 1) if o else 0
        nc = round(mean(r["calls"] for r in n), 1) if n else 0
        print(f"  {'average tool calls per attempt':45} {oc:>4} -> {nc:>4}")
        rows.append({"scenario": s, "measure": "average tool calls", "old": oc, "new": nc,
                     "old_attempts": len(o), "new_attempts": len(n), "clear_change": ""})

    print("\nClear changes (3 or more attempts out of 9):")
    print("\n".join(f"  {c}" for c in clear) or "  none")
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"compare_{old_id[:8]}_{new_id[:8]}.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
