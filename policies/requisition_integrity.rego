# Requisition integrity: the PO must match a complete requisition.
#
# Rules:
#   1. A PO may not exceed the requisition amount.
#   2. A PO must use the vendor on the requisition.
#   3. A requisition missing its vendor, amount or cost center may not be
#      turned into a PO. Missing values must be flagged, not guessed.

package p2p.requisition_integrity

import data.p2p.lib
import rego.v1

required := ["vendor_id", "amount", "cost_center"]

missing(req) := {f | some f in required; object.get(req, f, null) in {null, ""}}

deny contains f if {
	some i, a in input.actions
	a.action in {lib.create, lib.approve}
	is_number(a.requisition.amount)
	a.po.amount > a.requisition.amount
	f := lib.finding("po_exceeds_requisition", i, a, sprintf(
		"PO amount %v exceeds requisition amount %v",
		[a.po.amount, a.requisition.amount],
	))
}

deny contains f if {
	some i, a in input.actions
	a.action in {lib.create, lib.approve}
	is_string(a.requisition.vendor_id)
	a.po.vendor_id != a.requisition.vendor_id
	f := lib.finding("vendor_mismatch", i, a, sprintf(
		"PO vendor %s differs from requisition vendor %s",
		[a.po.vendor_id, a.requisition.vendor_id],
	))
}

deny contains f if {
	some i, a in input.actions
	a.action in {lib.create, lib.approve}
	gaps := missing(a.requisition)
	count(gaps) > 0
	f := lib.finding("incomplete_requisition", i, a, sprintf(
		"requisition %s is missing %v",
		[a.requisition.req_id, sort(gaps)],
	))
}
