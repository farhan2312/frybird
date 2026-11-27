import frappe

NEW_ITEMS = ["DRK-PEPSI", "DRK-MDEW", "DRK-MDEW-DIET", "DRK-7UP", "NUG-10", "SIDE-CHEESE", "ADD-BUN-PLAIN"]
# Where each new menu row goes: after the last row of this course, so the POS shows it with its category.
PLACE_AFTER = {"Drinks": "Drinks", "Chicken Nuggets": "Chicken Tenders", "Sides": "Sides", "Add-ons": "Add-ons"}


def execute():
	# Individual soft drinks (Pepsi, Mountain Dew, Mountain Dew Diet, 7UP next to Cola, all AED 4),
	# Chicken Nuggets (AED 10), Cheese Fries (AED 10) and a Normal Bun (AED 1).
	from ury.setup.frybird_store import ADDONS_BY_COURSE, BRANCH, IMG, MENU_ITEMS, OLD_BRANCH, PLATFORMS
	from ury.setup.aggregators import setup_delivery_platforms

	branch = next((b for b in (BRANCH, OLD_BRANCH) if frappe.db.exists("URY Restaurant", {"branch": b})), None)
	if not branch:
		return
	menu = frappe.get_doc("URY Menu", frappe.db.get_value("URY Restaurant", {"branch": branch}, "active_menu"))
	setup = {i[0]: i for i in MENU_ITEMS}

	# The generic soft drink becomes Cola, with a Cola photo.
	if frappe.db.exists("Item", "DRK-COLA"):
		frappe.db.set_value("Item", "DRK-COLA", "image", f"{IMG}{setup['DRK-COLA'][6]}.jpg")

	rows = list(menu.items)
	on_menu = {r.item for r in rows}
	added = False
	for code in NEW_ITEMS:
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
		new_row = frappe._dict(item=code, item_name=name, rate=price, course=course)
		cola = next((i for i, r in enumerate(rows) if r.item == "DRK-COLA"), None)
		if course == "Drinks" and cola is not None:
			rows.insert(cola, new_row)  # the soft drinks sit together, in order, just before Cola
		else:
			anchor = PLACE_AFTER.get(course, course)
			last = max((i for i, r in enumerate(rows) if r.course == anchor), default=len(rows) - 1)
			rows.insert(last + 1, new_row)
		added = True

	if added:
		menu.set("items", [])
		for r in rows:
			menu.append("items", {"item": r.item, "item_name": r.item_name, "rate": r.rate, "course": r.course,
								  "special_dish": r.get("special_dish") or 0, "disabled": r.get("disabled") or 0})
		menu.save(ignore_permissions=True)  # also rebuilds the menu's selling price list

	# Spice level on the new fries, like the other sides.
	for code in NEW_ITEMS:
		wanted = ADDONS_BY_COURSE.get(setup[code][2], [])
		if not wanted or not frappe.db.exists("Item", code):
			continue
		item = frappe.get_doc("Item", code)
		have = {a.item for a in item.custom_pos_add_on_items}
		missing = [c for c in wanted if c not in have and c != code]
		if missing:
			for c in missing:
				item.append("custom_pos_add_on_items", {"item": c})
			item.save(ignore_permissions=True)

	if added:  # price the new items on the delivery-app menus too
		setup_delivery_platforms(branch, platforms=[(n, markup) for n, markup, _ in PLATFORMS])
