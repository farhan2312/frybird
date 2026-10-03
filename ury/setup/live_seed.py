"""Make a FryBird demo site look like a restaurant that is trading right now.

Run after the setup wizard has loaded the FryBird demo masters:

    bench --site <site> execute ury.setup.live_seed.run
    bench --site <site> execute ury.setup.live_seed.run --kwargs '{"history_days": 30}'

Creates:
  * opening / closing checklists on the POS Profile
  * card payments, VAT-inclusive pricing, ~40 customers, Talabat and Keeta delivery platforms
  * `history_days` of closed shifts with lunch/dinner peaks, each with completed checklists
  * today's open shift: paid orders so far, occupied tables at every service stage,
    takeaway/delivery orders on the kitchen display. Today's opening checklist is left
    pending so the manager sees the checklist gate when opening the POS.
"""

import random
from datetime import datetime, timedelta

import frappe
from frappe.utils import now_datetime

BRANCH = "FryBird Whitehall"
PROFILE = "FryBird POS"
RESTAURANT = "FryBird"
OPENING_FLOAT = 500
SHIFT_START = (10, 45)  # cashier opens the till
SHIFT_END_AFTER_MIDNIGHT = (2, 30)  # late-night shop: last orders ~02:15, till closed 02:30
DAY_ROLLOVER_HOURS = 5  # matches URY Report Settings: sales before 05:00 belong to the previous day

OPENING_CHECKLIST = [
	("Fryer oil filtered and tested (TPM below 24%); changed if dark or foaming", 1),
	("Fryers at 175 °C before first drop", 1),
	("Chiller at or below 5 °C and freezer at or below -18 °C, logged on HACCP sheet", 1),
	("Raw chicken on bottom shelf, covered and labelled; thaw log checked", 1),
	("Marinated chicken, breading and wings prepped to lunch par levels", 1),
	("Hand-wash stations stocked: soap, paper towels, sanitiser", 1),
	("Staff in clean uniform, hairnets and gloves; fitness-to-work check done", 1),
	("Halal certificates valid and on display", 1),
	("Cash float counted (AED 500) and matches opening balance", 1),
	("Card terminal online; test transaction approved", 1),
	("Receipt and KOT printers loaded with paper; test print OK", 1),
	("Delivery tablets (Talabat, Deliveroo, Careem) online and accepting", 1),
	("Dining room and patio clean; tables and high chairs sanitised", 1),
	("Fire extinguisher and fire blanket in place; exits clear", 1),
	("Sauces and dips stocked: honey glaze, BBQ, hot, buffalo", 0),
	("Drinks fridge restocked and cold", 0),
	("Music, lighting and outdoor signage on", 0),
]
CLOSING_CHECKLIST = [
	("Fryers off; oil filtered and covered", 1),
	("Unsold chicken past holding time discarded and logged", 1),
	("Leftover raw stock labelled, dated and in chiller", 1),
	("Chiller and freezer temperatures logged at close", 1),
	("Grills, hoods, prep tables and floors cleaned", 1),
	("Cash counted, reconciled and safe drop done", 1),
	("Card terminal batch settlement done", 1),
	("Gas valves off; back door and front doors locked; alarm set", 1),
	("Waste log completed", 0),
	("Tomorrow's prep list written", 0),
]
REMARKS = [
	"Oil changed on fryer 2", "TPM 18%", "Chiller 3 °C / freezer -20 °C", "Short 2 kg wings, ordered",
	"Printer paper replaced", "Deliveroo tablet restarted", "Float verified by shift lead",
]

FIRST = ["Ahmed", "Mohammed", "Fatima", "Aisha", "Omar", "Khalid", "Mariam", "Yousef", "Sara", "Hamdan",
		 "Rahul", "Priya", "Arjun", "Anjali", "Joseph", "Maria", "John", "Grace", "Ali", "Noor",
		 "Hassan", "Layla", "Bilal", "Zainab", "Imran", "Ayesha", "Rohan", "Sneha", "Daniel", "Emily"]
LAST = ["Al Mansoori", "Al Nuaimi", "Khan", "Hussain", "Rahman", "Nair", "Menon", "Fernandes", "Santos",
		"Al Shamsi", "Sharma", "Iyer", "Qureshi", "Siddiqui", "Mathew", "Thomas", "Al Hashmi", "Farooq"]

# (item, popularity weight)
POPULAR = {
	"FC-2": 8, "FC-3": 9, "FC-5": 10, "FC-8": 5, "FC-10": 4, "FC-15": 2,
	"NG-8": 6, "NG-15": 3, "NG-20": 2,
	"WG-4": 5, "WG-6": 8, "WG-8": 5, "WG-10": 7, "WG-15": 2, "WG-20": 2,
	"TD-3": 7, "TD-6": 5, "TD-12": 2,
	"BG-CHK": 12, "BG-SPC": 9, "BG-BEEF": 8, "BG-DBL": 5, "BG-COMBO": 7,
}
SAUCES = ["SC-HNY", "SC-BBQ", "SC-HOT", "SC-BUF"]
# demand curve by hour of the business day (24-26 = 00:00-02:59 after midnight)
HOUR_WEIGHTS = {11: 2, 12: 7, 13: 9, 14: 6, 15: 3, 16: 2, 17: 3, 18: 5, 19: 8, 20: 10, 21: 10, 22: 8,
				23: 6, 24: 5, 25: 3, 26: 1}
ORDER_TYPES = [("Dine In", 35), ("Take Away", 22), ("Aggregators", 30), ("Delivery", 6), ("Phone In", 7)]
PLATFORM_SHARE = [("Talabat", 60), ("Keeta", 40)]


def wchoice(pairs):
	items, weights = zip(*pairs)
	return random.choices(items, weights=weights, k=1)[0]


def run(history_days=21, seed=7):
	random.seed(seed)
	frappe.flags.mute_messages = True
	frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 1)
	company = frappe.db.get_value("POS Profile", PROFILE, "company")
	if frappe.db.get_value("Company", company, "default_currency") == "AED":
		frappe.db.set_value("Currency", "AED", "symbol", "AED")  # "AED 29" reads clearer on the POS than "د.إ 29"
	setup_checklists()
	setup_card_payment(company)
	setup_vat(company)
	from ury.setup.aggregators import setup_delivery_platforms
	setup_delivery_platforms(BRANCH)
	seed_customers()
	from ury.setup.self_ordering import setup_self_ordering
	setup_self_ordering(BRANCH)
	ctx = build_ctx()
	close_stale_openings(ctx)
	frappe.db.commit()

	today = business_day(now_datetime())
	for offset in range(history_days, 0, -1):
		seed_closed_day(ctx, today - timedelta(days=offset))
		frappe.db.commit()
		print(f"seeded {today - timedelta(days=offset)}")

	seed_today(ctx)
	frappe.db.set_value("POS Profile", PROFILE, "custom_kot_warning_time", 15)
	frappe.db.commit()
	frappe.cache.delete_keys("bootinfo")
	print("FryBird live seed complete")


def refresh_live(seed=None):
	"""Start a fresh live shift without rebuilding history: run before a demo.

	Clears tonight's open orders and kitchen tickets, frees tables, closes the open shift (like a
	shift change) and seeds a new live shift up to the current time.
	"""
	random.seed(seed)
	frappe.flags.mute_messages = True
	ctx = build_ctx()
	for inv in frappe.get_all("POS Invoice", {"pos_profile": PROFILE, "docstatus": 0}, pluck="name"):
		frappe.db.set_value("URY KOT", {"invoice": inv, "docstatus": 1}, "order_status", "Served", update_modified=False)
		frappe.delete_doc("POS Invoice", inv, ignore_permissions=True, force=True)
	frappe.db.set_value("URY Table", {"branch": BRANCH}, {"occupied": 0, "latest_invoice_time": None})
	close_stale_openings(ctx)
	# the new shift starts at the manager's opening checklist again
	for log in frappe.get_all("URY POS Checklist Log", {"pos_profile": PROFILE, "checklist_type": "Opening",
														"shift_date": frappe.utils.nowdate()}, pluck="name"):
		frappe.delete_doc("URY POS Checklist Log", log, ignore_permissions=True, force=True)
	frappe.db.commit()
	seed_today(ctx)
	frappe.cache.delete_keys("bootinfo")
	print("FryBird live shift refreshed")


def build_ctx():
	ctx = frappe._dict()
	ctx.company = frappe.db.get_value("POS Profile", PROFILE, "company")
	ctx.warehouse = frappe.db.get_value("POS Profile", PROFILE, "warehouse")
	ctx.menu = frappe.db.get_value("URY Restaurant", RESTAURANT, "active_menu")
	ctx.price_list = frappe.db.get_value("Price List", {"restaurant_menu": ctx.menu, "enabled": 1})
	ctx.series = frappe.db.get_value("URY Restaurant", RESTAURANT, "invoice_series_prefix")
	ctx.prices = dict(frappe.get_all("Item Price", {"price_list": ctx.price_list}, ["item_code", "price_list_rate"], as_list=1))
	ctx.tables = frappe.get_all("URY Table", {"branch": BRANCH, "is_take_away": 0}, ["name", "restaurant_room", "no_of_seats"])
	ctx.cashier = "cashier@frybird.test"
	ctx.captain = "captain@frybird.test"
	ctx.manager = "manager@frybird.test"
	ctx.card = "Credit Card"
	ctx.tax_template = frappe.db.get_value("URY Restaurant", RESTAURANT, "default_tax_template")
	ctx.platform_prices = {
		p: dict(frappe.get_all("Item Price", {"price_list": f"{p} Menu"}, ["item_code", "price_list_rate"], as_list=1))
		for p, _ in PLATFORM_SHARE
	}
	ctx.agg_series = frappe.db.get_value("URY Restaurant", RESTAURANT, "aggregator_series_prefix")
	ctx.customers = ["Walk-In Customer"] + frappe.get_all(
		"Customer", {"customer_group": "Individual", "name": ["!=", "Walk-In Customer"]}, pluck="name")
	return ctx


# --------------------------------------------------------------------------- masters
def setup_checklists():
	profile = frappe.get_doc("POS Profile", PROFILE)
	profile.set("custom_checklist_items", [])
	for label, mandatory in OPENING_CHECKLIST:
		profile.append("custom_checklist_items", {"item_label": label, "applies_to": "Opening", "is_mandatory": mandatory})
	for label, mandatory in CLOSING_CHECKLIST:
		profile.append("custom_checklist_items", {"item_label": label, "applies_to": "Closing", "is_mandatory": mandatory})
	profile.save(ignore_permissions=True)


def setup_card_payment(company):
	mop = "Credit Card"
	if not frappe.db.exists("Mode of Payment", mop):
		frappe.get_doc({"doctype": "Mode of Payment", "mode_of_payment": mop, "type": "Bank"}).insert(ignore_permissions=True)
	account = frappe.db.get_value("Account", {"company": company, "account_name": "Card Settlements"})
	if not account:
		parent = frappe.db.get_value("Account", {"company": company, "account_type": "Bank", "is_group": 1}) or \
			frappe.db.get_value("Account", {"company": company, "account_name": ["like", "%Bank%"], "is_group": 1})
		account = frappe.get_doc({
			"doctype": "Account", "account_name": "Card Settlements", "company": company,
			"parent_account": parent, "account_type": "Bank", "is_group": 0,
		}).insert(ignore_permissions=True).name
	mop_doc = frappe.get_doc("Mode of Payment", mop)
	if not any(a.company == company for a in mop_doc.accounts):
		mop_doc.append("accounts", {"company": company, "default_account": account})
		mop_doc.save(ignore_permissions=True)

	profile = frappe.get_doc("POS Profile", PROFILE)
	if not any(p.mode_of_payment == mop for p in profile.payments):
		profile.append("payments", {"mode_of_payment": mop})
		profile.save(ignore_permissions=True)
	return mop


def setup_vat(company):
	"""UAE VAT 5%, included in menu prices (UAE requires VAT-inclusive display prices)."""
	template = frappe.db.get_value("Sales Taxes and Charges Template", {"company": company, "title": ["like", "%VAT 5%"]})
	if not template:
		return None
	doc = frappe.get_doc("Sales Taxes and Charges Template", template)
	for row in doc.taxes:
		row.included_in_print_rate = 1
	doc.is_default = 1
	doc.save(ignore_permissions=True)
	frappe.db.set_value("URY Restaurant", RESTAURANT, "default_tax_template", template)
	frappe.db.set_value("POS Profile", PROFILE, "taxes_and_charges", template)
	return template


def seed_customers(n=40):
	names = ["Walk-In Customer"]
	if not frappe.db.exists("Customer", "Walk-In Customer"):
		frappe.get_doc({"doctype": "Customer", "customer_name": "Walk-In Customer", "customer_group": "Individual",
						"territory": "All Territories"}).insert(ignore_permissions=True)
	seen = set()
	while len(names) < n + 1:
		name = f"{random.choice(FIRST)} {random.choice(LAST)}"
		if name in seen:
			continue
		seen.add(name)
		if not frappe.db.exists("Customer", name):
			frappe.get_doc({
				"doctype": "Customer", "customer_name": name, "customer_group": "Individual",
				"territory": "All Territories",
				"mobile_number": f"+971 5{random.choice('0245689')} {random.randint(100, 999)} {random.randint(1000, 9999)}",
			}).insert(ignore_permissions=True)
		names.append(name)
	return names


def close_stale_openings(ctx):
	"""Close shifts left open by the basic demo so today's shift is the only open one."""
	from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import make_closing_entry_from_opening

	for name in frappe.get_all("POS Opening Entry", {"status": "Open", "docstatus": 1, "pos_profile": PROFILE}, pluck="name"):
		closing = make_closing_entry_from_opening(frappe.get_doc("POS Opening Entry", name))
		closing.insert(ignore_permissions=True)
		closing.submit()


# --------------------------------------------------------------------------- orders
def pick_items():
	lines = {}
	for _ in range(random.choices([1, 2, 3, 4], weights=[35, 35, 20, 10])[0]):
		code = wchoice(POPULAR.items())
		lines[code] = lines.get(code, 0) + random.choices([1, 2, 3], weights=[75, 20, 5])[0]
	mains = sum(lines.values())
	if random.random() < 0.45:
		lines["ADD-MEAL"] = random.randint(1, mains)
	if random.random() < 0.15:
		lines["ADD-CHS"] = 1
	for _ in range(random.choices([0, 1, 2], weights=[55, 35, 10])[0]):
		s = random.choice(SAUCES)
		lines[s] = lines.get(s, 0) + 1
	return lines


def order_profile(ctx):
	order_type = wchoice(ORDER_TYPES)
	table = random.choice(ctx.tables) if order_type == "Dine In" else None
	pax = random.randint(1, min(int(table.no_of_seats or 4), 6)) if table else 1
	if order_type == "Aggregators":
		customer = wchoice(PLATFORM_SHARE)
	elif order_type in ("Dine In", "Take Away") and random.random() < 0.5:
		customer = "Walk-In Customer"
	else:
		customer = random.choice(ctx.customers[1:])
	return order_type, table, pax, customer


def make_paid_invoice(ctx, posting_dt, owner):
	order_type, table, pax, customer = order_profile(ctx)
	platform = customer if order_type == "Aggregators" else None
	prices = ctx.platform_prices[platform] if platform else ctx.prices
	inv = frappe.new_doc("POS Invoice")
	inv.update({
		"naming_series": ctx.agg_series if platform else ctx.series, "company": ctx.company, "pos_profile": PROFILE, "is_pos": 1, "update_stock": 1,
		"customer": customer, "set_posting_time": 1, "posting_date": posting_dt.date(),
		"posting_time": posting_dt.strftime("%H:%M:%S"),
		"selling_price_list": f"{platform} Menu" if platform else ctx.price_list, "custom_aggregator_id": platform,
		"restaurant": RESTAURANT, "branch": BRANCH, "order_type": order_type, "no_of_pax": str(pax),
		"waiter": ctx.captain if table else owner, "cashier": owner, "invoice_printed": 0,
		"restaurant_table": table.name if table else None,
		"custom_restaurant_room": table.restaurant_room if table else None,
		"taxes_and_charges": ctx.tax_template, "set_warehouse": ctx.warehouse,
	})
	for code, qty in pick_items().items():
		inv.append("items", {"item_code": code, "qty": qty, "rate": prices[code], "warehouse": ctx.warehouse})
	if ctx.tax_template:
		from erpnext.controllers.accounts_controller import get_taxes_and_charges
		inv.set("taxes", get_taxes_and_charges("Sales Taxes and Charges Template", ctx.tax_template))
	if platform:
		mop = platform  # settled by the platform, not at the till
	else:
		mop = ctx.card if (order_type == "Delivery" or random.random() < 0.6) else "Cash"
	inv.append("payments", {"mode_of_payment": mop, "amount": 0})
	inv.flags.ignore_permissions = True
	inv.insert()
	total = inv.rounded_total or inv.grand_total
	inv.payments[0].amount = total
	inv.paid_amount = total
	inv.db_set("invoice_printed", 1)  # bill printed at the counter; URY checks the saved flag before payment
	inv.submit()
	backdate(inv.doctype, inv.name, posting_dt, owner)
	return inv


def backdate(doctype, name, dt, owner=None):
	values = {"creation": dt, "modified": dt}
	if owner:
		values["owner"] = owner
	frappe.db.set_value(doctype, name, values, update_modified=False)


def business_day(dt):
	return (dt - timedelta(hours=DAY_ROLLOVER_HOURS)).date()


def at(day, hour, minute=0):
	"""Datetime on business `day`; hours >= 24 fall after midnight."""
	return datetime.combine(day, datetime.min.time()) + timedelta(hours=hour, minutes=minute)


def order_times(day, count, start, end):
	hours = [h for h in HOUR_WEIGHTS if at(day, h) <= end and at(day, h + 1) > start]
	times = []
	while len(times) < count and hours:
		h = random.choices(hours, weights=[HOUR_WEIGHTS[x] for x in hours])[0]
		t = at(day, h, random.randint(0, 59)) + timedelta(seconds=random.randint(0, 59))
		if start <= t <= end:
			times.append(t)
	return sorted(times)


def opening_entry(ctx, user, start_dt):
	doc = frappe.get_doc({
		"doctype": "POS Opening Entry", "company": ctx.company, "pos_profile": PROFILE, "user": user,
		"period_start_date": start_dt, "posting_date": start_dt.date(), "branch": BRANCH, "restaurant": RESTAURANT,
		"balance_details": [{"mode_of_payment": "Cash", "opening_amount": OPENING_FLOAT}],
	})
	doc.flags.ignore_permissions = True
	doc.insert()
	doc.submit()
	backdate(doc.doctype, doc.name, start_dt, user)
	return doc


def checklist_log(ctx, opening, day, kind, at):
	rows = OPENING_CHECKLIST if kind == "Opening" else CLOSING_CHECKLIST
	items = []
	for label, mandatory in rows:
		checked = 1 if mandatory or random.random() < 0.85 else 0
		items.append({"item_label": label, "is_mandatory": mandatory, "is_checked": checked,
					  "remarks": random.choice(REMARKS) if random.random() < 0.12 else None})
	log = frappe.get_doc({
		"doctype": "URY POS Checklist Log", "pos_profile": PROFILE, "branch": BRANCH, "checklist_type": kind,
		"pos_opening_entry": opening.name, "shift_date": day, "status": "Complete",
		"completed_by": ctx.manager, "completed_at": at, "items": items,
	})
	log.insert(ignore_permissions=True)
	backdate(log.doctype, log.name, at, ctx.manager)


def seed_closed_day(ctx, day):
	from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import make_closing_entry_from_opening

	start = at(day, *SHIFT_START)
	end = at(day, 24 + SHIFT_END_AFTER_MIDNIGHT[0], SHIFT_END_AFTER_MIDNIGHT[1])
	busy = day.weekday() in (3, 4, 5)  # Thu-Sat
	count = random.randint(60, 85) if busy else random.randint(38, 55)

	frappe.set_user(ctx.cashier)
	try:
		opening = opening_entry(ctx, ctx.cashier, start)
		checklist_log(ctx, opening, day, "Opening", start - timedelta(minutes=20))
		for t in order_times(day, count, start + timedelta(minutes=15), end - timedelta(minutes=15)):
			make_paid_invoice(ctx, t, ctx.cashier)
		closing = make_closing_entry_from_opening(opening)
		closing.posting_date = day
		closing.period_end_date = end
		closing.flags.ignore_permissions = True
		closing.insert()
		closing.submit()
		backdate(closing.doctype, closing.name, end, ctx.cashier)
		checklist_log(ctx, opening, day, "Closing", end + timedelta(minutes=25))
	finally:
		frappe.set_user("Administrator")


# --------------------------------------------------------------------------- today
def seed_today(ctx):
	from ury.ury.doctype.ury_order.ury_order import sync_order
	from ury.ury.api.ury_kot_display import serve_kot

	now = now_datetime()
	day = business_day(now)
	start = at(day, *SHIFT_START)
	early = start > now - timedelta(hours=1)
	if early:  # seeding before normal opening: run an early shift from just after the 05:00 day rollover
		start = at(day, DAY_ROLLOVER_HOURS, 5)
	last_paid = frappe.db.sql(
		"""select max(timestamp(posting_date, posting_time)) from `tabPOS Invoice`
		where pos_profile=%s and docstatus=1 and timestamp(posting_date, posting_time) >= %s""",
		(PROFILE, start),
	)[0][0]
	if last_paid and last_paid < now:  # shift change (refresh_live): carry on after the earlier shift's last sale
		start = last_paid + timedelta(minutes=1)

	# Administrator is the account you sign in with locally, so the open shift belongs to it.
	user = "Administrator"
	opening = opening_entry(ctx, user, start)

	# paid orders so far this shift (dashboard sales, order count, baseline)
	full_day = random.randint(60, 85) if day.weekday() in (3, 4, 5) else random.randint(38, 55)
	share = sum(w for h, w in HOUR_WEIGHTS.items() if at(day, h) < now) / sum(HOUR_WEIGHTS.values())
	window_start, window_end = start + timedelta(minutes=15), now - timedelta(minutes=20)
	if early or not any(at(day, h) < now for h in HOUR_WEIGHTS):
		span = (window_end - window_start).total_seconds()
		times = sorted(window_start + timedelta(seconds=random.uniform(0, span)) for _ in range(int(span / 3600 * 5))) if span > 0 else []
	else:
		times = order_times(day, max(int(full_day * share), 3), window_start, window_end)
	for t in times:
		make_paid_invoice(ctx, t, user)
	frappe.db.commit()

	# live tables: (table, minutes since seated, stage)
	live = [("D2", 4, "seated"), ("D3", 12, "fired"), ("D5", 22, "fired"), ("P1", 9, "fired"),
			("D6", 41, "served"), ("P3", 53, "served"), ("D8", 86, "served")]
	mop = "Cash"
	for table, minutes, stage in live:
		seated_at = now - timedelta(minutes=minutes)
		if stage == "seated":
			frappe.db.set_value("URY Table", table, {"occupied": 1, "latest_invoice_time": seated_at.strftime("%H:%M:%S")})
			continue
		res = sync_order(
			items=[{"item": c, "item_name": c, "rate": ctx.prices[c], "qty": q, "comment": ""} for c, q in pick_items().items()],
			cashier=user, owner=user, mode_of_payment=mop, customer=random.choice(ctx.customers),
			no_of_pax=random.randint(2, 4), last_invoice=None, waiter=ctx.captain, pos_profile=PROFILE, table=table,
			order_type="Dine In",
		)
		inv_name = res.get("name") if isinstance(res, dict) else getattr(res, "name", None)
		age_live_order(inv_name, seated_at, served=(stage == "served"), serve_kot=serve_kot)
		frappe.db.set_value("URY Table", table, {"occupied": 1, "latest_invoice_time": seated_at.strftime("%H:%M:%S")})

	# counter and delivery-app orders on the kitchen display
	for order_type, minutes, platform in [("Take Away", 6, None), ("Aggregators", 11, "Talabat"), ("Take Away", 2, None),
										  ("Aggregators", 4, "Keeta"), ("Phone In", 15, None), ("Aggregators", 8, "Talabat")]:
		prices = ctx.platform_prices[platform] if platform else ctx.prices
		res = sync_order(
			items=[{"item": c, "item_name": c, "rate": prices[c], "qty": q, "comment": ""} for c, q in pick_items().items()],
			cashier=user, owner=user, mode_of_payment=platform or mop,
			customer=platform or random.choice(ctx.customers[1:]),
			no_of_pax=1, last_invoice=None, waiter=user, pos_profile=PROFILE, order_type=order_type,
			aggregator_id=platform,
		)
		inv_name = res.get("name") if isinstance(res, dict) else getattr(res, "name", None)
		age_live_order(inv_name, now - timedelta(minutes=minutes), served=False, serve_kot=serve_kot)

	frappe.db.commit()


def age_live_order(invoice, placed_at, served, serve_kot):
	if not invoice:
		return
	backdate("POS Invoice", invoice, placed_at)
	for kot in frappe.get_all("URY KOT", {"invoice": invoice, "docstatus": 1}, pluck="name"):
		backdate("URY KOT", kot, placed_at + timedelta(minutes=1))
		frappe.db.set_value("URY KOT", kot, "start_time_prep", (placed_at + timedelta(minutes=1)).strftime("%H:%M:%S"),
							update_modified=False)
		if served:
			serve_kot(kot)
