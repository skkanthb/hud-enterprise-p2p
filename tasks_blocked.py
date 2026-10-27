"""Experiment tasks: what does an AI agent do when the system says no?

6 clean-looking requisitions x 7 modes = 42 tasks. See blocked.py.
The nudged modes were added later; tasks_nudged.py, tasks_clean.py and tasks_dated.py run them.
"""

from blocked import MODES, REQUISITIONS, bank_change_block, env

tasks = [bank_change_block(variant=v, mode=m) for m in MODES for v in range(len(REQUISITIONS))]

__all__ = ["env", "tasks"]
