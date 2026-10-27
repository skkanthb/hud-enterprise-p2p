"""Print the reason the agent gave whenever it stopped instead of approving.

Usage (from the repo root):
    ~/.local/share/uv/tools/hud/bin/python scripts/show_stops.py JOB_ID
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from summarize_jobs import Hud  # noqa: E402
from summarize_blocked import find  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: show_stops.py JOB_ID")
    hud = Hud()
    for tid in hud.trace_ids(sys.argv[1]):
        info = find(hud.trace(tid).get("evaluation_result"))
        if not info or info.get("approved_any"):
            continue
        state = info.get("erp_state", {})
        reasons = [r["reason"] for r in state.get("escalations", []) + state.get("flags", [])]
        print(f"\n== {info['req_id']} ({info['mode']}): {info['category']}")
        for r in reasons:
            print(f"   recorded reason: {r}")
        print(f"   final answer: {info.get('final_answer')}")


if __name__ == "__main__":
    main()
