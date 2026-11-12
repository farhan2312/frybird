import frappe


def execute():
	# Noon Food was added to the store setup after sites were built, so it never reached the POS.
	from ury.setup.frybird_store import BRANCH, OLD_BRANCH, PLATFORMS
	from ury.setup.aggregators import setup_delivery_platforms

	branch = next((b for b in (BRANCH, OLD_BRANCH) if frappe.db.exists("URY Restaurant", {"branch": b})), None)
	if not branch:
		return
	for name, markup, commission in PLATFORMS:
		if name == "Noon Food":
			setup_delivery_platforms(branch, platforms=[(name, markup)])
			frappe.db.set_value("Customer", name, "customer_details", f"Delivery platform. Commission {commission}% of order value.")
