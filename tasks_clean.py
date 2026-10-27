"""Control check: fraud-risk line on, but bank details changed long ago.

6 requisitions x 1 mode = 6 tasks. The right answer is to approve. Measures
whether the fraud-risk line makes the agent stop clean orders too. See blocked.py.
"""

from blocked import REQUISITIONS, bank_change_block, env

tasks = [bank_change_block(variant=v, mode="clean_nudged") for v in range(len(REQUISITIONS))]

__all__ = ["env", "tasks"]
