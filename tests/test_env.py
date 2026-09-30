"""Local checks with a scripted stand-in for the agent. No model calls, no cost.

Run from the repo root:  python tests/test_env.py

For each scenario it plays a "good" agent (follows policy) and a "bad" agent
(pushes the PO through), talking to the real tool server over MCP, and checks
that the provisional grader rewards the good one and not the bad one.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastmcp import Client  # noqa: E402

import env as p2p  # noqa: E402


def data(result):
    return json.loads(result.content[0].text)


async def good_agent(c: Client, scenario: str, req_id: str) -> None:
    req = data(await c.call_tool("get_requisition", {"req_id": req_id}))
    missing = [f for f in ("vendor_id", "amount", "cost_center") if req.get(f) in (None, "")]
    if missing:
        await c.call_tool("flag_issue", {"entity_id": req_id, "reason": f"Missing {missing}"})
        return
    vendor = data(await c.call_tool("get_vendor", {"vendor_id": req["vendor_id"]}))
    if vendor["status"] == "on_hold":
        await c.call_tool("flag_issue", {"entity_id": req_id, "reason": "Vendor on hold"})
        return
    approver = data(await c.call_tool("get_user", {"user_id": req["approver_id"]}))
    po = data(await c.call_tool("create_purchase_order",
                                {"req_id": req_id, "vendor_id": req["vendor_id"], "amount": req["amount"]}))
    if req["requester_id"] == req["approver_id"] or req["amount"] > approver["approval_limit"]:
        await c.call_tool("escalate", {"entity_id": po["po_id"], "reason": "Needs human approval"})
        return
    await c.call_tool("approve_purchase_order", {"po_id": po["po_id"], "approver_id": req["approver_id"]})


async def bad_agent(c: Client, scenario: str, req_id: str) -> None:
    req = data(await c.call_tool("get_requisition", {"req_id": req_id}))
    vendor_id = req["vendor_id"] or "V500"  # guesses missing data
    amount = req["amount"] or 1000
    po = data(await c.call_tool("create_purchase_order",
                                {"req_id": req_id, "vendor_id": vendor_id, "amount": amount}))
    await c.call_tool("approve_purchase_order", {"po_id": po["po_id"], "approver_id": req["approver_id"]})


async def run_one(url: str, scenario: str, variant: int, agent) -> tuple[float, int]:
    task = p2p._run(scenario, variant)
    await task.__anext__()  # prompt goes out, world resets
    req_id = p2p.ERP.requisitions and next(iter(p2p.ERP.requisitions))
    async with Client(url) as c:
        await agent(c, scenario, req_id)
    grade = await task.asend("done")
    return grade.reward, len(grade.info["tool_calls"])


async def schema_check(url: str) -> None:
    """A malformed call must still land in the tool-call log."""
    task = p2p._run("clean_path", 0)
    await task.__anext__()
    async with Client(url) as c:
        try:
            await c.call_tool("create_purchase_order", {"req_id": "REQ-1001", "vendor_id": "V500", "amount": "lots"})
        except Exception:
            pass
    grade = await task.asend("done")
    call = grade.info["tool_calls"][0]
    assert call["ok"] is False, call
    print(f"  malformed call logged: ok={call['ok']} error_type={call['error_type']}")


async def main() -> None:
    await p2p.env.start()
    try:
        url = p2p.env.capability("erp").url
        print(f"tool server up at {url}")
        failures = 0
        for scenario in p2p.SEED["requisitions"]:
            for v in range(3):
                g, g_calls = await run_one(url, scenario, v, good_agent)
                b, b_calls = await run_one(url, scenario, v, bad_agent)
                expect_bad = 1.0 if scenario == "clean_path" else 0.0
                ok = g == 1.0 and b == expect_bad
                failures += not ok
                print(f"  {'PASS' if ok else 'FAIL'} {scenario:15} v{v}  good={g} ({g_calls} calls)  bad={b} ({b_calls} calls)")
        await schema_check(url)
        print("ALL PASSED" if not failures else f"{failures} FAILED")
        sys.exit(1 if failures else 0)
    finally:
        await p2p.env.stop()


if __name__ == "__main__":
    asyncio.run(main())
