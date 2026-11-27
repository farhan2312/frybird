import frappe

# Old category -> new one. Sando moves to Sandwiches on its own.
NEW_COURSE = {
	"Fried Chicken": "Fryd Pieces",
	"Chicken Nuggets": "Fryd Pieces",
	"Chicken Tenders": "Chicken Tenders",
	"Burgers": "Burgers",
	"Meals": "Burgers",
	"Wraps": "Sandwiches",
	"Sides": "Add On",
	"Add-ons": "Add On",
	"Dips": "Add On",
	"Drinks": "Drinks",
}


def execute():
	# The POS and captain tablet show only six categories: Fryd Pieces, Chicken Tenders, Burgers,
	# Sandwiches, Add On, Drinks. Kitchen stations (item groups) and add-ons are not touched.
	from ury.setup.frybird_store import MENU_COURSES

	for course in MENU_COURSES:
		if not frappe.db.exists("URY Menu Course", course):
			frappe.get_doc({"doctype": "URY Menu Course", "course": course}).insert(ignore_permissions=True)

	for name in frappe.get_all("URY Menu", filters={"enabled": 1}, pluck="name"):
		menu = frappe.get_doc("URY Menu", name)
		rows = []
		for row in menu.items:
			course = "Sandwiches" if row.item == "BRG-SANDO" else NEW_COURSE.get(row.course, row.course)
			rows.append((row, course))
		order = {c: i for i, c in enumerate(MENU_COURSES)}
		# Group rows by category in the six-category order, keeping each category's current item order.
		rows.sort(key=lambda r: order.get(r[1], len(order)))
		menu.set("items", [])
		for row, course in rows:
			menu.append("items", {"item": row.item, "item_name": row.item_name, "rate": row.rate, "course": course,
								  "special_dish": row.special_dish, "disabled": row.disabled})
		menu.save(ignore_permissions=True)
