"""Fair re-run of the fraud-line checks, with today's date in the prompt.

6 risky (recent bank change) + 6 clean (old bank change) = 12 tasks.
Added after the agent said it could not tell how recent the change was.
See blocked.py.
"""

from blocked import REQUISITIONS, bank_change_block, env

tasks = [bank_change_block(variant=v, mode=m)
         for m in ("off_nudged_dated", "clean_nudged_dated") for v in range(len(REQUISITIONS))]

__all__ = ["env", "tasks"]
