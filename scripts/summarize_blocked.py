"""Summarize a run of the blocked-approval experiment (tasks_blocked.py).

Usage (from the repo root):
    ~/.local/share/uv/tools/hud/bin/python scripts/summarize_blocked.py JOB_ID

Prints, per mode, what the agent did, plus how each requisition went.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from summarize_jobs import Hud  # noqa: E402

MODES = ["off", "off_nudged", "clean_nudged", "off_nudged_dated", "clean_nudged_dated", "enforced", "enforced_instructed"]
FLAGS = ["blocked", "retried_same_approver", "tried_other_approver", "created_new_po_after_block",
         "used_other_vendor", "claimed_success", "routed", "reason_given", "mentioned_bank_change"]


def find(ev):
    if isinstance(ev, dict):
        if ev.get("scenario") == "bank_change_block" and "mode" in ev:
            return ev
        for v in ev.values():
            got = find(v)
            if got:
                return got
    return {}


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: summarize_blocked.py JOB_ID")
    job = sys.argv[1]
    hud = Hud()
    print(f"\n{hud.model_name(job)}  (job {job})")
    cats = defaultdict(Counter)
    flags = defaultdict(Counter)
    per_req = defaultdict(lambda: defaultdict(Counter))
    errors = 0
    for tid in hud.trace_ids(job):
        t = hud.trace(tid)
        if t.get("error"):
            errors += 1
            continue
        info = find(t.get("evaluation_result"))
        if not info:
            errors += 1
            continue
        m = info["mode"]
        cats[m][info["category"]] += 1
        for f in FLAGS:
            flags[m][f] += bool(info.get(f))
        per_req[m][info["req_id"]][info["category"]] += 1
    for m in MODES:
        n = sum(cats[m].values())
        if not n:
            continue
        print(f"\n== {m}  ({n} attempts)")
        for c, k in cats[m].most_common():
            print(f"  {k:>3}  {c}")
        print("  details: " + ", ".join(f"{f} {flags[m][f]}" for f in FLAGS))
        for r in sorted(per_req[m]):
            print(f"    {r}: " + "; ".join(f"{c} x{k}" for c, k in per_req[m][r].items()))
    print(f"\nExcluded (technical errors): {errors}")


if __name__ == "__main__":
    main()
