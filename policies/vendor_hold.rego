# Vendor holds: no purchase order may be raised or approved for a vendor on hold.

package p2p.vendor_hold

import data.p2p.lib
import rego.v1

deny contains f if {
	some i, a in input.actions
	a.action in {lib.create, lib.approve}
	a.vendor.status == "on_hold"
	f := lib.finding("vendor_on_hold", i, a, sprintf(
		"%s involves vendor %s, which is on hold",
		[a.action, a.vendor.vendor_id],
	))
}
