import frappe


def execute():
	# "Ranchy Dip" is called "Dip Ranch", like Dip Garlic and Dip Dynamite.
	if not frappe.db.exists("Item", "DIP-RANCHY"):
		return
	frappe.db.set_value("Item", "DIP-RANCHY", {"item_name": "Dip Ranch", "description": "Dip Ranch"})
	frappe.db.sql("UPDATE `tabURY Menu Item` SET item_name = 'Dip Ranch' WHERE item = 'DIP-RANCHY'")
	frappe.db.sql("UPDATE `tabItem Price` SET item_name = 'Dip Ranch' WHERE item_code = 'DIP-RANCHY'")
