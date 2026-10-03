"""Customer self-ordering (/order) for a branch: table QR codes and pickup QR.

    bench --site <site> execute ury.setup.self_ordering.setup_self_ordering --kwargs '{"branch": "FryBird Whitehall"}'

Creates (idempotently) a URY Self Ordering Profile with QR table + pickup ordering on. Staff then print the
codes from /table-qr (URY Manager / System Manager).
"""

import frappe

PROFILE_NAME = "FryBird Self Order"


def setup_self_ordering(branch, profile_name=PROFILE_NAME, default_customer="Walk-In Customer"):
	restaurant = frappe.db.get_value("URY Restaurant", {"branch": branch}, "name")
	pos_profile = frappe.db.get_value("POS Profile", {"branch": branch, "disabled": 0}, "name")
	if not restaurant or not pos_profile:
		frappe.throw(f"Branch {branch} needs a URY Restaurant and a POS Profile before self ordering")

	if frappe.db.exists("URY Self Ordering Profile", profile_name):
		doc = frappe.get_doc("URY Self Ordering Profile", profile_name)
	else:
		doc = frappe.new_doc("URY Self Ordering Profile")
		doc.name = profile_name
	doc.update({
		"profile_name": profile_name, "restaurant": restaurant, "branch": branch, "pos_profile": pos_profile,
		"default_customer": default_customer if frappe.db.exists("Customer", default_customer) else None,
		"enabled": 1, "enable_qr_table_ordering": 1, "enable_qr_pickup_ordering": 1,
		"allow_add_to_running_table": 1, "show_item_images": 1, "show_item_descriptions": 1,
		"enable_item_notes": 1, "enable_product_detail_page": 1,
		"enable_request_bill": 1, "enable_pay_at_counter": 1,
	})
	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)
	frappe.db.commit()
	return doc.name
