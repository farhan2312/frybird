import frappe


def execute():
	# Adds any add-on in the store setup that a live site is missing (Extra Chicken Strip, spice level on fries)
	# and offers it on every item of its menu course, without touching anything staff changed.
	from ury.setup.frybird_store import ADDONS_BY_COURSE, BRANCH, IMG, MENU_ITEMS, OLD_BRANCH, PLATFORMS
	from ury.setup.aggregators import setup_delivery_platforms

	branch = next((b for b in (BRANCH, OLD_BRANCH) if frappe.db.exists("URY Restaurant", {"branch": b})), None)
	if not branch:
		return
	menu = frappe.get_doc("URY Menu", frappe.db.get_value("URY Restaurant", {"branch": branch}, "active_menu"))
	on_menu = {r.item for r in menu.items}
	setup = {i[0]: i for i in MENU_ITEMS}
	addon_codes = list(dict.fromkeys(code for codes in ADDONS_BY_COURSE.values() for code in codes))

	added = False
	for code in addon_codes:
		if code in on_menu:
			continue
		_, name, course, group, price, desc, img = setup[code]
		if not frappe.db.exists("Item Group", group):
			frappe.get_doc({"doctype": "Item Group", "item_group_name": group, "parent_item_group": "All Item Groups"}).insert(ignore_permissions=True)
		if not frappe.db.exists("URY Menu Course", course):
			frappe.get_doc({"doctype": "URY Menu Course", "course": course}).insert(ignore_permissions=True)
		if not frappe.db.exists("Item", code):
			frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": name, "item_group": group, "description": desc or name,
							"is_stock_item": 0, "is_sales_item": 1, "stock_uom": "Nos", "image": f"{IMG}{img}.jpg"}).insert(ignore_permissions=True)
		menu.append("items", {"item": code, "item_name": name, "rate": price, "course": course})
		added = True
	if added:
		menu.save(ignore_permissions=True)  # also rebuilds the menu's selling price list

	for row in menu.items:
		wanted = [c for c in ADDONS_BY_COURSE.get(row.course, []) if c != row.item]
		if not wanted:
			continue
		item = frappe.get_doc("Item", row.item)
		have = {a.item for a in item.custom_pos_add_on_items}
		missing = [c for c in wanted if c not in have]
		if missing:
			for code in missing:
				item.append("custom_pos_add_on_items", {"item": code})
			item.save(ignore_permissions=True)

	if added:  # price the new add-ons on the delivery-app menus too
		setup_delivery_platforms(branch, platforms=[(n, markup) for n, markup, _ in PLATFORMS])
