import frappe


def execute():
	# The Orders page has a Recently Paid tab only when paid_limit is set.
	frappe.db.sql("update `tabPOS Profile` set paid_limit = 20 where coalesce(paid_limit, 0) = 0")
