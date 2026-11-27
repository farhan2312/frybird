import frappe

CODE = "MEAL-CHK-BURGER"


def execute():
	# Chicken Burger Meal is off the menu. The item stays (disabled) so past orders and reports keep it.
	for name in frappe.get_all("URY Menu", filters={"enabled": 1}, pluck="name"):
		menu = frappe.get_doc("URY Menu", name)
		rows = [r for r in menu.items if r.item != CODE]
		if len(rows) == len(menu.items):
			continue
		menu.set("items", [])
		for r in rows:
			menu.append("items", {"item": r.item, "item_name": r.item_name, "rate": r.rate, "course": r.course,
								  "special_dish": r.special_dish, "disabled": r.disabled})
		menu.save(ignore_permissions=True)  # also drops its price from the menu price list
	if frappe.db.exists("Item", CODE):
		frappe.db.set_value("Item", CODE, "disabled", 1)
	# It was priced on the delivery-app menus too.
	frappe.db.delete("Item Price", {"item_code": CODE, "price_list": ["in", ["Talabat Menu", "Keeta Menu", "Noon Food Menu"]]})
