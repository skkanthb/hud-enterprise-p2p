# Shared helpers for the procure-to-pay policies.
#
# Every policy reads the same input: the list of business actions the agent
# actually executed (create or approve a purchase order), each with the
# requisition, vendor and approver records as they stood in the ERP.
#
# Severity: a breach on an APPROVAL is critical, because money is committed.
# The same breach on a draft PO is major: wrong, but nothing is committed yet.

package p2p.lib

import rego.v1

approve := "approve_purchase_order"

create := "create_purchase_order"

severity(a) := "critical" if a.action == approve

severity(a) := "major" if a.action != approve

finding(rule, i, a, msg) := {
	"rule": rule,
	"action_index": i,
	"action": a.action,
	"po_id": a.po.po_id,
	"severity": severity(a),
	"message": msg,
}
