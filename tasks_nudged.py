"""Follow-up tasks: system check off, plus one general line about fraud risk.

6 requisitions x 1 mode = 6 tasks. Answers the question: does the agent catch
the bank-change signal when asked to watch for fraud in general? See blocked.py.
"""

from blocked import REQUISITIONS, bank_change_block, env

tasks = [bank_change_block(variant=v, mode="off_nudged") for v in range(len(REQUISITIONS))]

__all__ = ["env", "tasks"]
