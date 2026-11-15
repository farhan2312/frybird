import frappe

CODE = "ADD-SPICY-SEASONING"


def execute():
	# Paid Spicy Seasoning add-on (AED 3) on every fried chicken and tenders item, for sites built before it existed.
	from ury.setup.frybird_store import ADDONS_BY_COURSE, BRANCH, IMG, MENU_ITEMS, OLD_BRANCH, PLATFORMS
	from ury.setup.aggregators import setup_delivery_platforms

	branch = next((b for b in (BRANCH, OLD_BRANCH) if frappe.db.exists("URY Restaurant", {"branch": b})), None)
	if not branch:
		return
	code, name, course, group, price, desc, img = next(i for i in MENU_ITEMS if i[0] == CODE)
	if not frappe.db.exists("Item Group", group):
		frappe.get_doc({"doctype": "Item Group", "item_group_name": group, "parent_item_group": "All Item Groups"}).insert(ignore_permissions=True)
	if not frappe.db.exists("URY Menu Course", course):
		frappe.get_doc({"doctype": "URY Menu Course", "course": course}).insert(ignore_permissions=True)
	if not frappe.db.exists("Item", CODE):
		frappe.get_doc({"doctype": "Item", "item_code": CODE, "item_name": name, "item_group": group, "description": desc,
						"is_stock_item": 0, "is_sales_item": 1, "stock_uom": "Nos", "image": f"{IMG}{img}.jpg"}).insert(ignore_permissions=True)

	# The add-on must be on the menu (that gives it its price) before items can offer it.
	menu_name = frappe.db.get_value("URY Restaurant", {"branch": branch}, "active_menu")
	menu = frappe.get_doc("URY Menu", menu_name)
	if not any(r.item == CODE for r in menu.items):
		menu.append("items", {"item": CODE, "item_name": name, "rate": price, "course": course})
		menu.save(ignore_permissions=True)  # also rebuilds the menu's selling price list

	chicken_courses = [c for c, addons in ADDONS_BY_COURSE.items() if CODE in addons]
	for row in menu.items:
		if row.course in chicken_courses and row.item != CODE:
			item = frappe.get_doc("Item", row.item)
			if not any(a.item == CODE for a in item.custom_pos_add_on_items):
				item.append("custom_pos_add_on_items", {"item": CODE})
				item.save(ignore_permissions=True)

	# Price it on the delivery-app menus too (in-store +markup, like every other item).
	setup_delivery_platforms(branch, platforms=[(n, markup) for n, markup, _ in PLATFORMS])
