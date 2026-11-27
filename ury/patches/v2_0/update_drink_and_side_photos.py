import frappe

CODES = ["DRK-PEPSI", "DRK-MDEW", "DRK-MDEW-DIET", "DRK-7UP", "DRK-COLA", "NUG-10", "SIDE-CHEESE"]


def execute():
	# Photos supplied by FryBird for the soft drinks, Chicken Nuggets and Cheese Fries.
	from ury.setup.frybird_store import IMG, MENU_ITEMS

	setup = {i[0]: i for i in MENU_ITEMS}
	for code in CODES:
		if frappe.db.exists("Item", code):
			frappe.db.set_value("Item", code, "image", f"{IMG}{setup[code][6]}.jpg")
	# The POS reloads its menu when the menu's modified time changes, so mark the menus changed.
	for menu in frappe.get_all("URY Menu", filters={"enabled": 1}, pluck="name"):
		frappe.db.set_value("URY Menu", menu, "modified", frappe.utils.now(), update_modified=False)
