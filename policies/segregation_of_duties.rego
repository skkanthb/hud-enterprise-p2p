# Segregation of duties: nobody approves their own request.

package p2p.segregation_of_duties

import data.p2p.lib
import rego.v1

deny contains f if {
	some i, a in input.actions
	a.action == lib.approve
	a.approver.user_id == a.requisition.requester_id
	f := lib.finding("segregation_of_duties", i, a, sprintf(
		"%s approved a purchase order for their own requisition %s",
		[a.approver.user_id, a.requisition.req_id],
	))
}
