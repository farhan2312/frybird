"""Set up FryBird for real trading on a fresh site: the store masters without any demo history.

Run after the ERPNext setup wizard (company, currency, chart of accounts) has completed:

    bench --site <site> execute ury.setup.store_setup.setup_store

Loads from ury/setup/demo_data only the masters a working store needs (menu, item groups, courses, branch,
rooms, tables, POS profile, kitchen stations, report settings, combo bundle), then configures checklists,
card payments, VAT-inclusive pricing, Talabat/Keeta, QR self-ordering and branding. It creates no sales,
customers (except Walk-In Customer), suppliers, employees or users. Menu dishes are not stock items, and raw
ingredients start at zero stock. Safe to run again.
"""

import json
import os

import frappe

from ury.setup.demo import replace_placeholders

BRANCH = "FryBird Whitehall"
DATA_DIR = os.path.join(os.path.dirname(__file__), "demo_data")
# dependency order (branch before menu/rooms, restaurant before tables and POS profile, POS profile before kitchens)
MASTERS = [
	"item_group", "item", "item_price", "product_bundle", "branch", "ury_menu_course", "ury_menu", "ury_room",
	"ury_restaurant", "ury_table", "pos_profile", "ury_production_unit", "ury_report_settings",
]
STAFF_ROLES = ["URY Manager", "URY Cashier", "URY Captain"]


def setup_store(company=None):
	company = company or frappe.defaults.get_global_default("company") or frappe.get_all("Company", pluck="name")[0]
	warehouse = _stores_warehouse(company)
	frappe.flags.mute_messages = True

	for name in MASTERS:
		for record in _load(name):
			_transform(name, record)
			_set(record, "__WAREHOUSE__", warehouse)  # before replace_placeholders, which would pick a random one
			replace_placeholders(record, company)
			_insert(record)
		frappe.db.commit()

	_walk_in_customer()
	frappe.get_doc("User", "Administrator").add_roles(*STAFF_ROLES)

	from ury.install import set_frybird_branding
	from ury.setup import live_seed
	from ury.setup.aggregators import setup_delivery_platforms
	from ury.setup.self_ordering import setup_self_ordering

	if frappe.db.get_value("Company", company, "default_currency") == "AED":
		frappe.db.set_value("Currency", "AED", "symbol", "AED")
	live_seed.setup_checklists()
	live_seed.setup_card_payment(company)
	live_seed.setup_vat(company)
	setup_delivery_platforms(BRANCH)
	setup_self_ordering(BRANCH)
	set_frybird_branding()
	frappe.db.commit()
	frappe.flags.mute_messages = False
	return "FryBird store ready"


def _load(name):
	with open(os.path.join(DATA_DIR, f"{name}.json"), encoding="utf-8") as f:
		return json.load(f)


def _transform(name, record):
	if name == "item":
		record.pop("opening_stock", None)
		if not record["item_code"].startswith("RM-"):
			record["is_stock_item"] = "0"  # dishes are made to order; stock is tracked on raw ingredients
	elif name == "branch":
		record["user"] = [{"user": "Administrator"}]  # real staff are added when their accounts exist
	elif name == "pos_profile":
		record["applicable_for_users"] = [
			{"doctype": "POS Profile User", "user": "Administrator", "default": "1", "parentfield": "applicable_for_users"}
		]


def _set(data, placeholder, value):
	if isinstance(data, dict):
		for k, v in data.items():
			if v == placeholder:
				data[k] = value
			else:
				_set(v, placeholder, value)
	elif isinstance(data, list):
		for v in data:
			_set(v, placeholder, value)


def _insert(record):
	doc = frappe.get_doc(record)
	try:
		doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
	except (frappe.DuplicateEntryError, frappe.UniqueValidationError):
		pass
	except Exception as e:
		if "Duplicate" in type(e).__name__ or "ItemPriceDuplicateItem" in type(e).__name__:
			return
		raise


def _stores_warehouse(company):
	return (
		frappe.db.get_value("Warehouse", {"company": company, "is_group": 0, "warehouse_name": "Stores"})
		or frappe.db.get_value("Warehouse", {"company": company, "is_group": 0})
	)


def _walk_in_customer():
	if not frappe.db.exists("Customer", "Walk-In Customer"):
		frappe.get_doc({"doctype": "Customer", "customer_name": "Walk-In Customer", "customer_group": "Individual",
						"territory": "All Territories"}).insert(ignore_permissions=True)
