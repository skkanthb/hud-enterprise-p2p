"""The task set: 8 scenarios x 3 variants = 24 tasks.

The first five are the plain scenarios. The last three add realistic pressure:
a note on the requisition that argues for breaking policy.
"""

from env import (
    blocked_vendor,
    clean_path,
    env,
    freight_over_limit,
    missing_data,
    over_limit,
    sod_trap,
    urgency_override,
    vendor_hold_pressure,
)

TEMPLATES = [
    clean_path,
    over_limit,
    sod_trap,
    blocked_vendor,
    missing_data,
    urgency_override,
    vendor_hold_pressure,
    freight_over_limit,
]

tasks = [template(variant=v) for template in TEMPLATES for v in range(3)]

__all__ = ["env", "tasks"]
