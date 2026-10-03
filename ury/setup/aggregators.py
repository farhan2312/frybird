"""Delivery platforms (Talabat, Keeta) as URY aggregators.

    bench --site <site> execute ury.setup.aggregators.setup_delivery_platforms --kwargs '{"branch": "FryBird Whitehall"}'

For each platform this creates (idempotently):
  * a Customer (the platform is the billed party; customer group "Delivery Platforms")
  * a selling Price List "<Platform> Menu" = in-store menu price x (1 + markup), rounded up to whole units,
    to absorb the platform commission
  * a Mode of Payment "<Platform>" posting to a "<Platform> Settlements" account (the platform pays out weekly)
  * an Aggregator Settings row on the Branch, which makes it selectable under the POS "Aggregators" order type
and adds the payment modes to the branch's POS Profiles.
"""

import math

import frappe

PLATFORMS = [
	# name, markup over in-store price
	("Talabat", 0.15),
	("Keeta", 0.15),
]
CUSTOMER_GROUP = "Delivery Platforms"


def setup_delivery_platforms(branch, platforms=None, series_prefix="FBA-"):
	platforms = platforms or PLATFORMS
	restaurant = frappe.db.get_value("URY Restaurant", {"branch": branch}, ["name", "active_menu", "company"], as_dict=True)
	if not restaurant:
		frappe.throw(f"No URY Restaurant for branch {branch}")
	company = restaurant.company or frappe.db.get_value("POS Profile", {"branch": branch}, "company")
	currency = frappe.db.get_value("Company", company, "default_currency")
	base_list = frappe.db.get_value("Price List", {"restaurant_menu": restaurant.active_menu, "enabled": 1})
	base_prices = frappe.get_all("Item Price", {"price_list": base_list}, ["item_code", "price_list_rate", "uom"])

	if not frappe.db.exists("Customer Group", CUSTOMER_GROUP):
		frappe.get_doc({"doctype": "Customer Group", "customer_group_name": CUSTOMER_GROUP,
						"parent_customer_group": "All Customer Groups"}).insert(ignore_permissions=True)

	branch_doc = frappe.get_doc("Branch", branch)
	for name, markup in platforms:
		customer = _customer(name)
		price_list = _price_list(name, currency, base_prices, markup)
		mop = _mode_of_payment(name, company)
		row = next((r for r in branch_doc.custom_aggregator_settings if r.customer == customer), None)
		if not row:
			row = branch_doc.append("custom_aggregator_settings", {})
		row.customer, row.price_list, row.mode_of_payments = customer, price_list, mop
		for profile in frappe.get_all("POS Profile", {"branch": branch}, pluck="name"):
			_add_payment_mode(profile, mop)
	branch_doc.custom_no_taxes = 0  # platform prices are VAT-inclusive like the in-store menu
	branch_doc.custom_make_unpaid = 0  # orders are settled through the platform's mode of payment
	branch_doc.save(ignore_permissions=True)

	if not frappe.db.get_value("URY Restaurant", restaurant.name, "aggregator_series_prefix"):
		frappe.db.set_value("URY Restaurant", restaurant.name, "aggregator_series_prefix", series_prefix)
	frappe.db.commit()
	return [c for c, _ in platforms]


def _customer(name):
	if not frappe.db.exists("Customer", name):
		frappe.get_doc({"doctype": "Customer", "customer_name": name, "customer_group": CUSTOMER_GROUP,
						"territory": "All Territories", "customer_type": "Company"}).insert(ignore_permissions=True)
	return name


def _price_list(platform, currency, base_prices, markup):
	name = f"{platform} Menu"
	if not frappe.db.exists("Price List", name):
		frappe.get_doc({"doctype": "Price List", "price_list_name": name, "currency": currency,
						"selling": 1, "enabled": 1}).insert(ignore_permissions=True)
	for p in base_prices:
		rate = math.ceil(p.price_list_rate * (1 + markup))
		existing = frappe.db.get_value("Item Price", {"price_list": name, "item_code": p.item_code})
		if existing:
			frappe.db.set_value("Item Price", existing, "price_list_rate", rate)
		else:
			frappe.get_doc({"doctype": "Item Price", "price_list": name, "item_code": p.item_code,
							"uom": p.uom, "price_list_rate": rate, "selling": 1}).insert(ignore_permissions=True)
	return name


def _mode_of_payment(platform, company):
	if not frappe.db.exists("Mode of Payment", platform):
		frappe.get_doc({"doctype": "Mode of Payment", "mode_of_payment": platform, "type": "Bank"}).insert(ignore_permissions=True)
	account_name = f"{platform} Settlements"
	account = frappe.db.get_value("Account", {"company": company, "account_name": account_name})
	if not account:
		parent = frappe.db.get_value("Account", {"company": company, "account_type": "Bank", "is_group": 1}) or \
			frappe.db.get_value("Account", {"company": company, "account_name": ["like", "%Bank%"], "is_group": 1})
		account = frappe.get_doc({"doctype": "Account", "account_name": account_name, "company": company,
								  "parent_account": parent, "account_type": "Bank", "is_group": 0}).insert(ignore_permissions=True).name
	mop = frappe.get_doc("Mode of Payment", platform)
	if not any(a.company == company for a in mop.accounts):
		mop.append("accounts", {"company": company, "default_account": account})
		mop.save(ignore_permissions=True)
	return platform


def _add_payment_mode(profile_name, mop):
	profile = frappe.get_doc("POS Profile", profile_name)
	if not any(p.mode_of_payment == mop for p in profile.payments):
		profile.append("payments", {"mode_of_payment": mop})
		profile.save(ignore_permissions=True)
