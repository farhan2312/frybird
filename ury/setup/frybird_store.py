"""FryBird Cafe Ajman - the client's finalized store data (docs/FryBird_Client_Information_Form.xlsx, Oct 2026).

Applies company details, branch, tables, menu (flyer prices, AED incl. VAT), kitchen stations and staff to a site
that was set up with ury.setup.store_setup. Safe to run again.

    from ury.setup.frybird_store import apply
    apply(default_password="...")   # password for newly created staff only; never stored in this repo
"""

import frappe

COMPANY_NAME = "Frybird Cafe LLC"
COMPANY_DETAILS = {
	"tax_id": "105222735000001",  # VAT TRN
	"registration_details": "Trade Licence No. 134013",
	"phone_no": "+971 54 349 7170",
	"email": "frybirdcafe@gmail.com",
	"website": "https://frybird.ae",
}
OLD_BRANCH, BRANCH = "FryBird Whitehall", "FryBird Cafe Ajman"
RESTAURANT, PROFILE, MENU = "FryBird", "FryBird POS", "FryBird Menu"
ADDRESS = {"address_line1": "Al Hamideya 1", "city": "Ajman", "state": "Ajman", "country": "United Arab Emirates",
		   "phone": "+971 54 349 7170", "email_id": "frybirdcafe@gmail.com"}
CASH_FLOAT = 150

# area, table, seats, shape, room type
TABLES = [
	("Dining Room", "D1", 6, "Rectangle", "AC"), ("Dining Room", "D2", 6, "Rectangle", "AC"),
	("Dining Room", "D3", 2, "Square", "AC"), ("Dining Room", "D4", 2, "Rectangle", "AC"),
	("Patio", "P1", 4, "Rectangle", "NON-AC"), ("Patio", "P2", 4, "Rectangle", "NON-AC"),
	("Patio", "P3", 4, "Rectangle", "NON-AC"), ("Patio", "P4", 4, "Rectangle", "NON-AC"),
	("Patio", "P5", 4, "Rectangle", "NON-AC"),
]

# kitchen stations -> item groups they prepare (Counter items get no kitchen ticket)
STATIONS = {
	"Fry Station": ["FRIED CHICKEN", "CHICKEN TENDERS", "SIDES"],
	"Grill Station": ["BURGERS", "WRAPS"],
	"Drinks Station": ["DRINKS"],
}
OLD_STATION_GROUPS = ["FRIED CHICKEN", "WINGS", "TENDERS", "NUGGETS", "SIDES", "BURGERS", "COMBOS"]

IMG = "/assets/ury/Images/menu/"  # real/ = product photos from the FryBird flyer
# code, name, course (menu category), item group (decides kitchen station), price AED, description, image
MENU_ITEMS = [
	("FCH-OS-2", "2 PCS Original Spicy Fried Chicken", "Fried Chicken", "FRIED CHICKEN", 10, "", "real/fried-chicken-original"),
	("FCH-OS-4", "4 PCS Original Spicy Fried Chicken", "Fried Chicken", "FRIED CHICKEN", 19, "", "real/fried-chicken-original"),
	("FCH-OS-9", "9 PCS Original Spicy Fried Chicken", "Fried Chicken", "FRIED CHICKEN", 39, "", "real/fried-chicken-original"),
	("FCH-NH-2", "2 PCS Nash Hot Fried Chicken", "Fried Chicken", "FRIED CHICKEN", 16, "", "real/fried-chicken-nash-hot"),
	("FCH-NH-4", "4 PCS Nash Hot Fried Chicken", "Fried Chicken", "FRIED CHICKEN", 29, "", "real/fried-chicken-nash-hot"),
	("FCH-LH-2", "2 PCS Lemon Hot Fried Chicken", "Fried Chicken", "FRIED CHICKEN", 16, "", "real/fried-chicken-lemon-hot"),
	("FCH-LH-4", "4 PCS Lemon Hot Fried Chicken", "Fried Chicken", "FRIED CHICKEN", 29, "", "real/fried-chicken-lemon-hot"),
	("TND-OS-2", "2 PCS Original Spicy Chicken Tenders", "Chicken Tenders", "CHICKEN TENDERS", 10, "", "real/tenders-original"),
	("TND-OS-4", "4 PCS Original Spicy Chicken Tenders", "Chicken Tenders", "CHICKEN TENDERS", 19, "", "real/tenders-original"),
	("TND-OS-6", "6 PCS Original Spicy Chicken Tenders", "Chicken Tenders", "CHICKEN TENDERS", 28, "", "real/tenders-original"),
	("TND-NH-2", "2 PCS Nash Hot Chicken Tenders", "Chicken Tenders", "CHICKEN TENDERS", 16, "", "real/tenders-nash-hot"),
	("TND-NH-4", "4 PCS Nash Hot Chicken Tenders", "Chicken Tenders", "CHICKEN TENDERS", 29, "", "real/tenders-nash-hot"),
	("TND-NH-6", "6 PCS Nash Hot Chicken Tenders", "Chicken Tenders", "CHICKEN TENDERS", 42, "", "real/tenders-nash-hot"),
	("TND-LH-2", "2 PCS Lemon Hot Chicken Tenders", "Chicken Tenders", "CHICKEN TENDERS", 16, "", "real/tenders-lemon-hot"),
	("TND-LH-4", "4 PCS Lemon Hot Chicken Tenders", "Chicken Tenders", "CHICKEN TENDERS", 29, "", "real/tenders-lemon-hot"),
	("TND-LH-6", "6 PCS Lemon Hot Chicken Tenders", "Chicken Tenders", "CHICKEN TENDERS", 42, "", "real/tenders-lemon-hot"),
	("BRG-CLASSIC", "Classic Burger", "Burgers", "BURGERS", 10, "Crispy chicken burger", "real/burger-classic"),
	("BRG-RANCHY", "Ranchy Burger", "Burgers", "BURGERS", 15, "Crispy chicken burger", "real/burger-ranchy"),
	("BRG-NASH", "Nash Burger", "Burgers", "BURGERS", 15, "Crispy chicken burger", "real/burger-nash"),
	("BRG-CHEESY", "Cheesy Classic Burger", "Burgers", "BURGERS", 15, "Crispy chicken burger", "real/burger-cheesy-classic"),
	("BRG-SANDO", "Sando", "Burgers", "BURGERS", 20, "Crispy chicken sandwich", "real/sando"),
	("BRG-BUFFALO", "Buffalo Ranch", "Burgers", "BURGERS", 25, "Crispy chicken burger", "real/buffalo-ranch"),
	("BRG-CHEESE", "Cheese Burger", "Burgers", "BURGERS", 16, "Beef burger", "real/burger-cheese"),
	("BRG-BIGCHEESE", "Big Cheese", "Burgers", "BURGERS", 20, "Beef burger", "real/burger-big-cheese"),
	("BRG-PRIME", "Prime House", "Burgers", "BURGERS", 25, "Beef burger", "real/burger-prime-house"),
	("WRP-MINI", "Mini Wrap", "Wraps", "WRAPS", 6, "", "real/wrap"),
	("WRP-SUPREME", "Supreme Wrap", "Wraps", "WRAPS", 10, "", "real/wrap"),
	("WRP-RANCHY", "Ranchy Wrap", "Wraps", "WRAPS", 15, "", "real/wrap"),
	("SIDE-FRIES", "Fries", "Sides", "SIDES", 5, "", "ADD-MEAL"),
	("SIDE-SPICY", "Spicy Fries", "Sides", "SIDES", 8, "", "ADD-MEAL"),
	("SIDE-LOADED", "Loaded Fries", "Sides", "SIDES", 15, "", "ADD-CHS"),
	("SIDE-FRYBIRD", "FryBird Fries", "Sides", "SIDES", 20, "", "ADD-CHS"),
	("ADD-MEAL-FD", "Meal with Fries & Drink", "Add-ons", "ADD-ONS", 7, "Upgrade any item to a meal", None),
	("ADD-BUN", "Brioche Bun", "Add-ons", "BURGERS", 2, "", None),  # grill makes it, so it shares the burger group
	("DRK-COLA", "Cola", "Drinks", "DRINKS", 4, "", "drink-cola"),
	("DRK-LEMONADE", "Lemonade", "Drinks", "DRINKS", 4, "", "drink-lemonade"),
	("DRK-SHAKE-OREO", "Milkshake - Oreo", "Drinks", "DRINKS", 10, "", "shake-oreo"),
	("DRK-SHAKE-KINDER", "Milkshake - Kinder", "Drinks", "DRINKS", 10, "", "shake-kinder"),
	("DRK-SHAKE-LOTUS", "Milkshake - Lotus", "Drinks", "DRINKS", 10, "", "shake-lotus"),
	("DRK-SHAKE-PB", "Peanut Butter Shake", "Drinks", "DRINKS", 15, "", "shake-peanut-butter"),
	("DRK-WATER", "Water", "Drinks", "DRINKS", 1, "", "drink-water"),
	("DIP-GARLIC", "Garlic Dip", "Dips", "DIPS", 2, "", "dip-garlic"),
	("DIP-RANCHY", "Ranchy Dip", "Dips", "DIPS", 2, "", "dip-ranchy"),
	("DIP-DYNAMITE", "Dynamite Dip", "Dips", "DIPS", 2, "", "dip-dynamite"),
]

STAFF_ROLES = {
	"Owner": ["System Manager", "URY Admin", "URY Manager", "URY Cashier", "URY Captain", "Self Ordering Manager",
			  "Accounts Manager", "Accounts User", "Sales Manager", "Sales User", "Stock Manager", "Stock User",
			  "Purchase Manager", "Purchase User", "Item Manager"],
	"Manager": ["URY Manager", "URY Cashier", "URY Captain", "Self Ordering Manager", "Stock User", "Purchase User",
				"Sales User", "Item Manager"],
	"Cashier": ["URY Cashier", "URY Captain"],
	"Waiter": ["URY Captain"],
	"Kitchen": ["URY Captain"],  # kitchen display (mosaic) needs URY KOT read/write, which Captain has
}
# username, full name, email, mobile, role
STAFF = [
	("kavind", "Kavind", "kavind@frybird.ae", "+971 50 791 1047", "Manager"),
	("safwan", "Safwan", "safwan@frybird.ae", "+91 79025 96055", "Waiter"),
	("anas", "Anas", "anas@frybird.ae", None, "Kitchen"),
	("shehin", "Shehin", "shehin@frybird.ae", None, "Kitchen"),
	("irshad", "Irshad", "irshad@frybird.ae", None, "Kitchen"),
	("raees", "Raees", "raees@frybird.ae", "+971 54 427 0544", "Owner"),
]


def apply(default_password=None):
	frappe.flags.mute_messages = True
	company = _company()
	_branch()
	_tables()
	_menu()
	_stations()
	_cash_float_checklist()
	if default_password:
		_staff(default_password)
	from ury.setup.aggregators import setup_delivery_platforms
	from ury.setup.self_ordering import setup_self_ordering
	setup_delivery_platforms(BRANCH)  # rebuild Talabat/Keeta price lists from the new menu
	setup_self_ordering(BRANCH)
	frappe.db.commit()
	frappe.clear_cache()
	frappe.flags.mute_messages = False
	return f"{company} / {BRANCH}: {len(TABLES)} tables, {len(MENU_ITEMS)} menu items, {len(STAFF)} staff"


def _company():
	current = frappe.get_all("Company", pluck="name")[0]
	if current != COMPANY_NAME:
		frappe.rename_doc("Company", current, COMPANY_NAME, force=True)
	frappe.db.set_value("Company", COMPANY_NAME, COMPANY_DETAILS)
	frappe.db.set_default("company", COMPANY_NAME)
	frappe.db.set_single_value("Global Defaults", "default_company", COMPANY_NAME)
	name = frappe.db.get_value("Dynamic Link", {"link_doctype": "Company", "link_name": COMPANY_NAME, "parenttype": "Address"}, "parent")
	addr = frappe.get_doc("Address", name) if name else frappe.new_doc("Address")
	addr.update({"address_title": COMPANY_NAME, "address_type": "Billing", "is_your_company_address": 1, **ADDRESS})
	if not name:
		addr.append("links", {"link_doctype": "Company", "link_name": COMPANY_NAME})
	addr.save(ignore_permissions=True)
	return COMPANY_NAME


def _branch():
	if frappe.db.exists("Branch", OLD_BRANCH) and not frappe.db.exists("Branch", BRANCH):
		frappe.rename_doc("Branch", OLD_BRANCH, BRANCH, force=True)


def _tables():
	for room, _, _, _, room_type in TABLES:
		if not frappe.db.exists("URY Room", room):
			doc = frappe.new_doc("URY Room")
			doc.name = room
			doc.update({"branch": BRANCH, "room_type": room_type})
			doc.insert(ignore_permissions=True)
		else:
			frappe.db.set_value("URY Room", room, {"branch": BRANCH, "room_type": room_type})
	wanted = {t[1] for t in TABLES}
	for name in frappe.get_all("URY Table", {"branch": BRANCH}, pluck="name"):
		if name not in wanted and not frappe.db.exists("POS Invoice", {"restaurant_table": name}):
			frappe.delete_doc("URY Table", name, ignore_permissions=True, force=True)
	for room, table, seats, shape, _ in TABLES:
		values = {"restaurant": RESTAURANT, "restaurant_room": room, "branch": BRANCH, "no_of_seats": seats,
				  "table_shape": shape, "is_take_away": 0}
		if frappe.db.exists("URY Table", table):
			frappe.db.set_value("URY Table", table, values)
		else:
			doc = frappe.new_doc("URY Table")
			doc.name = table
			doc.update(values)
			doc.insert(ignore_permissions=True)
	frappe.db.set_value("URY Restaurant", RESTAURANT, "default_room", TABLES[0][0])


def _menu():
	for group in sorted({i[3] for i in MENU_ITEMS}):
		if not frappe.db.exists("Item Group", group):
			frappe.get_doc({"doctype": "Item Group", "item_group_name": group, "parent_item_group": "All Item Groups"}).insert(ignore_permissions=True)
	for course in dict.fromkeys(i[2] for i in MENU_ITEMS):
		if not frappe.db.exists("URY Menu Course", course):
			frappe.get_doc({"doctype": "URY Menu Course", "course": course}).insert(ignore_permissions=True)
	for code, name, _, group, _, desc, img in MENU_ITEMS:
		values = {"item_name": name, "item_group": group, "description": desc or name, "is_stock_item": 0,
				  "is_sales_item": 1, "stock_uom": "Nos", "disabled": 0, "image": f"{IMG}{img}.jpg" if img else None}
		if frappe.db.exists("Item", code):
			frappe.db.set_value("Item", code, values)
		else:
			frappe.get_doc({"doctype": "Item", "item_code": code, **values}).insert(ignore_permissions=True)
	menu = frappe.get_doc("URY Menu", MENU)
	new_codes = {i[0] for i in MENU_ITEMS}
	old_codes = [r.item for r in menu.items if r.item not in new_codes]
	menu.set("items", [])
	for code, name, course, _, price, _, _ in MENU_ITEMS:
		menu.append("items", {"item": code, "item_name": name, "rate": price, "course": course})
	menu.branch = BRANCH
	menu.save(ignore_permissions=True)  # also rebuilds the menu's selling price list
	for code in old_codes:  # demo menu items: hide, keep history intact
		frappe.db.set_value("Item", code, "disabled", 1)
	for bundle in frappe.get_all("Product Bundle", pluck="name"):
		if bundle not in new_codes:
			frappe.db.set_value("Product Bundle", bundle, "disabled", 1)


def _stations():
	for station, groups in STATIONS.items():
		if frappe.db.exists("URY Production Unit", station):
			doc = frappe.get_doc("URY Production Unit", station)
		else:
			doc = frappe.new_doc("URY Production Unit")
			doc.production = station
		doc.update({"pos_profile": PROFILE, "branch": BRANCH})
		doc.set("item_groups", [{"item_group": g} for g in groups])
		doc.save(ignore_permissions=True)


def _cash_float_checklist():
	profile = frappe.get_doc("POS Profile", PROFILE)
	for row in profile.custom_checklist_items:
		if row.item_label.startswith("Cash float counted"):
			row.item_label = f"Cash float counted (AED {CASH_FLOAT}) and matches opening balance"
	profile.save(ignore_permissions=True)


def _staff(password):
	branch = frappe.get_doc("Branch", BRANCH)
	profile = frappe.get_doc("POS Profile", PROFILE)
	for username, full_name, email, mobile, role in STAFF:
		created = not frappe.db.exists("User", email)
		user = frappe.new_doc("User") if created else frappe.get_doc("User", email)
		if created:
			user.update({"email": email, "first_name": full_name, "send_welcome_email": 0})
			user.new_password = password
			user.flags.ignore_password_policy = True
		user.update({"username": username, "user_type": "System User", "enabled": 1})
		if mobile:
			user.mobile_no = mobile
		for r in STAFF_ROLES[role]:
			if frappe.db.exists("Role", r) and r not in [x.role for x in user.roles]:
				user.append("roles", {"role": r})
		user.save(ignore_permissions=True) if not created else user.insert(ignore_permissions=True)
		if not any(x.user == email for x in branch.user):
			branch.append("user", {"user": email})
		if role in ("Owner", "Manager", "Cashier") and not any(x.user == email for x in profile.applicable_for_users):
			profile.append("applicable_for_users", {"user": email})
	branch.save(ignore_permissions=True)
	profile.save(ignore_permissions=True)
