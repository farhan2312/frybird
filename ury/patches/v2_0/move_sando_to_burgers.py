import frappe


def execute():
	# Sando is listed under Burgers, back in its place after the Cheesy Classic Burger.
	for name in frappe.get_all("URY Menu", filters={"enabled": 1}, pluck="name"):
		menu = frappe.get_doc("URY Menu", name)
		sando = next((r for r in menu.items if r.item == "BRG-SANDO"), None)
		if not sando or sando.course == "Burgers":
			continue
		rows = [r for r in menu.items if r is not sando]
		after = next((i for i, r in enumerate(rows) if r.item == "BRG-CHEESY"), None)
		if after is None:
			after = max((i for i, r in enumerate(rows) if r.course == "Burgers"), default=len(rows) - 1)
		sando.course = "Burgers"
		rows.insert(after + 1, sando)
		menu.set("items", [])
		for r in rows:
			menu.append("items", {"item": r.item, "item_name": r.item_name, "rate": r.rate, "course": r.course,
								  "special_dish": r.special_dish, "disabled": r.disabled})
		menu.save(ignore_permissions=True)
