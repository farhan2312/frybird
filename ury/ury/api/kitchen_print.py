"""Print documents for the FryBird Android app on the counter terminal (see android/).

The server can't reach printers on the shop network, so the app collects kitchen tickets from here
and sends them to the kitchen printer itself. Layout lives here so it can change without a new app.

A print document is a list of lines: {"t": text, "b": bold, "s": 1, 2, 3 or 4 (normal, double, double height, double width), "a": "l", "c" or "r"}.
A kitchen ticket can also carry "beep": raw printer bytes as hex, sent after the ticket.
"""

import json
import textwrap
import unicodedata

import frappe
from frappe import _
from frappe.utils import add_to_date, flt, format_datetime, get_datetime, now_datetime

from ury.ury.api.self_ordering import CURBSIDE_PREFIX

PRINT_ROLE = "URY Print Agent"
PRINT_USER = "printer@frybird.ae"
TICKET_HEADER = "FRYBIRD AJMAN"
TICKET_ITEM_SIZE = 4  # double width at normal height, like the shop's old tickets
WIDTH = 48  # characters per line at normal size on 80mm paper
TICKET_ITEM_WIDTH = WIDTH // 2
# Sounds the buzzer so the kitchen hears a new ticket. Printers differ, so this sends the common ways and each printer
# ignores the ones it doesn't know: ESC B 3 2 (built-in buzzer, 3 beeps), ESC p on pins 2 and 5 (a buzzer or bell
# on the drawer socket), and BEL.
TICKET_BEEP = "1b420302" "1b700019fa" "1b700119fa" "07"
CASH_MODE = "Cash"
ORDER_TYPE_LABELS = {"Delivery": "Home Delivery"}
TICKET_MAX_AGE_HOURS = 2  # anything older is stale for the kitchen, so it isn't printed late
CANCEL_TYPES = ("Partially cancelled", "Cancelled")
TICKET_TITLES = {"Order Modified": "ADDED TO ORDER", "Partially cancelled": "CANCELLED ITEMS", "Cancelled": "ORDER CANCELLED"}


def setup_print_agent():
	"""Create the app's login and return its API key. Running it again issues a new secret.

	bench --site <site> execute ury.ury.api.kitchen_print.setup_print_agent
	"""
	if not frappe.db.exists("Role", PRINT_ROLE):
		frappe.get_doc({"doctype": "Role", "role_name": PRINT_ROLE, "desk_access": 0}).insert(ignore_permissions=True)
	if frappe.db.exists("User", PRINT_USER):
		user = frappe.get_doc("User", PRINT_USER)
	else:
		user = frappe.get_doc({"doctype": "User", "email": PRINT_USER, "first_name": "Kitchen Printer", "send_welcome_email": 0, "user_type": "System User"})
		user.insert(ignore_permissions=True)
	if PRINT_ROLE not in [r.role for r in user.roles]:
		user.append("roles", {"role": PRINT_ROLE})
	user.api_key = user.api_key or frappe.generate_hash(length=15)
	secret = frappe.generate_hash(length=15)
	user.api_secret = secret
	user.save(ignore_permissions=True)
	frappe.db.commit()
	return {"api_key": user.api_key, "api_secret": secret}


@frappe.whitelist()
def get_pending_tickets():
	_require_agent()
	cutoff = add_to_date(now_datetime(), hours=-TICKET_MAX_AGE_HOURS)
	kots = frappe.get_all(
		"URY KOT",
		filters={"docstatus": 1, "kitchen_printed": 0, "type": ["!=", "Duplicate"], "creation": [">=", cutoff]},
		fields=["name", "invoice", "type", "production", "order_no", "restaurant_table", "table_takeaway", "aggregator_id", "comments", "creation", "user"],
		order_by="creation asc, name asc",
	)
	# One order creates a KOT per station; the kitchen has one printer, so they print as one ticket.
	groups = {}
	for kot in kots:
		groups.setdefault((kot.invoice, kot.type in CANCEL_TYPES), []).append(kot)
	return [{"kots": [k.name for k in group], "lines": _ticket_lines(group), "beep": TICKET_BEEP} for group in groups.values()]


@frappe.whitelist(methods=["POST"])
def mark_tickets_printed(kots):
	_require_agent()
	for name in json.loads(kots) if isinstance(kots, str) else kots:
		frappe.db.set_value("URY KOT", name, "kitchen_printed", 1, update_modified=False)
	return {"status": "ok"}


@frappe.whitelist()
def get_receipt(invoice):
	doc = frappe.get_doc("POS Invoice", invoice)
	if not frappe.has_permission("POS Invoice", "read", doc=doc):
		frappe.throw(_("Not permitted to print this invoice"), frappe.PermissionError)
	return {"lines": _receipt_lines(doc)}


@frappe.whitelist()
def get_shift_summary(opening_entry, end, sub_cashier=0):
	"""A short end-of-day slip for Close POS: items sold, sales, payments by mode and the cash that should be in the drawer."""
	opening = frappe.get_doc("POS Opening Entry", opening_entry)
	if not frappe.has_permission("POS Opening Entry", "read", doc=opening):
		frappe.throw(_("Not permitted to print this shift"), frappe.PermissionError)
	# The same invoices Close POS counts, so the slip matches the closing screen.
	if int(sub_cashier or 0):
		from ury.ury.doctype.sub_pos_closing.sub_pos_closing import get_pos_invoices
	else:
		from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import get_pos_invoices
	rows = get_pos_invoices(opening.period_start_date, end, opening.pos_profile, opening.user)
	invoices = [frappe.get_doc("POS Invoice", row.get("name")) for row in rows]
	return {"lines": _summary_lines(opening, invoices, end)}


def _summary_lines(opening, invoices, end):
	company = frappe.db.get_value("POS Profile", opening.pos_profile, "company")
	items, payments = {}, {}
	sales = discount = vat = qty = 0
	for doc in invoices:
		for item in doc.items:
			sold = items.setdefault(item.item_name, [0, 0])
			sold[0] += flt(item.qty)
			sold[1] += flt(item.amount)
			qty += flt(item.qty)
		for payment in doc.payments:
			payments[payment.mode_of_payment] = payments.get(payment.mode_of_payment, 0) + flt(payment.amount)
		if flt(doc.change_amount):
			payments[CASH_MODE] = payments.get(CASH_MODE, 0) - flt(doc.change_amount)
		sales += flt(doc.rounded_total or doc.grand_total)
		discount += flt(doc.discount_amount)
		vat += flt(doc.total_taxes_and_charges)
	cancelled = frappe.get_all(
		"POS Invoice",
		filters={"owner": opening.user, "pos_profile": opening.pos_profile, "docstatus": 2,
				 "creation": ["between", [opening.period_start_date, end]]},
		fields=["grand_total"],
	)

	lines = [
		_line(frappe.db.get_value("Company", company, "company_name") or company, bold=True, size=2, align="c"),
		_line("END OF DAY SUMMARY", bold=True, align="c"),
		_divider(),
		_line(f"Shift: {format_datetime(opening.period_start_date, 'dd MMM HH:mm')} - {format_datetime(get_datetime(end), 'dd MMM HH:mm')}"),
		_line(f"Cashier: {frappe.utils.get_fullname(opening.user)}"),
		_divider(),
	]
	for name, (sold_qty, amount) in sorted(items.items(), key=lambda row: (-row[1][0], row[0])):
		lines.append(_columns(f"{sold_qty:g} x {name}", _money(amount)))
	if not items:
		lines.append(_line("No sales"))
	lines += [
		_divider(),
		_columns("Orders", str(len(invoices))),
		_columns("Items sold", f"{qty:g}"),
	]
	if discount:
		lines.append(_columns("Discounts", f"-{_money(discount)}"))
	lines += [_columns("VAT", _money(vat)), _columns("TOTAL SALES", _money(sales), bold=True), _divider()]
	for mode, amount in sorted(payments.items(), key=lambda row: -row[1]):
		if amount:
			lines.append(_columns(mode, _money(amount)))
	opening_cash = sum(flt(row.opening_amount) for row in opening.balance_details if row.mode_of_payment == CASH_MODE)
	lines += [
		_divider(),
		_columns("Opening cash", _money(opening_cash)),
		_columns("Cash in drawer", _money(opening_cash + payments.get(CASH_MODE, 0)), bold=True),
	]
	if cancelled:
		lines.append(_columns(f"Cancelled orders ({len(cancelled)})", _money(sum(flt(c.grand_total) for c in cancelled))))
	lines += [_divider(), _line(f"Printed {format_datetime(now_datetime(), 'dd MMM yyyy HH:mm')}", align="c")]
	return lines


def _require_agent():
	roles = frappe.get_roles()
	if PRINT_ROLE not in roles and "System Manager" not in roles:
		frappe.throw(_("Not permitted"), frappe.PermissionError)


def _ticket_lines(kots):
	first = kots[0]
	invoice = frappe.db.get_value("POS Invoice", first.invoice, ["order_type", "custom_comments"], as_dict=True) or frappe._dict()
	is_cancel = first.type in CANCEL_TYPES
	lines = [
		_line(TICKET_HEADER, align="c"),
		_line(f"KOT# {first.order_no or first.invoice}", bold=True, size=2, align="c"),
		_line("." * WIDTH),
		_columns("Date", format_datetime(first.creation, "d-M-yyyy")),
		_columns("Time", format_datetime(first.creation, "HH:mm")),
		_divider(),
		_line(_ticket_destination(first, invoice), bold=True, size=2, align="c"),
	]
	if first.type != "New Order":
		lines.append(_line(TICKET_TITLES.get(first.type, first.type), bold=True, align="c"))
	lines += [_divider(), _line("QTY  ITEM")]
	total_qty = 0
	for kot in kots:
		if len(kots) > 1:
			station = frappe.db.get_value("URY Production Unit", kot.production, "production") or kot.production or ""
			lines.append(_line(station.upper()))
		for item in frappe.get_all("URY KOT Items", filters={"parent": kot.name}, fields=["item_name", "quantity", "cancelled_qty", "comments"], order_by="idx"):
			qty = item.cancelled_qty if is_cancel else item.quantity
			total_qty += flt(qty)
			lines += [_line(text, bold=True, size=TICKET_ITEM_SIZE) for text in _wrap(f"{qty} x {item.item_name}", indent="  ", width=TICKET_ITEM_WIDTH)]
			if item.comments:
				lines += [_line(text, size=TICKET_ITEM_SIZE) for text in _wrap(f"  {item.comments}", indent="  ", width=TICKET_ITEM_WIDTH)]
	if first.comments and not first.comments.startswith(CURBSIDE_PREFIX):
		lines += [_divider()] + [_line(text, size=TICKET_ITEM_SIZE) for text in _wrap(f"Note: {first.comments}", indent="  ", width=TICKET_ITEM_WIDTH)]
	lines += [_divider(), _columns("Waiter", first.user or ""), _columns("TotalQty", f"{total_qty:g}"), _divider()]
	return lines


def _ticket_destination(kot, invoice):
	if (kot.comments or "").startswith(CURBSIDE_PREFIX):
		return "Car " + kot.comments[len(CURBSIDE_PREFIX):]
	if kot.aggregator_id:
		return kot.aggregator_id
	if kot.restaurant_table and not kot.table_takeaway:
		return f"Table {kot.restaurant_table}"
	return ORDER_TYPE_LABELS.get(invoice.order_type, invoice.order_type) or "Take Away"


def _receipt_lines(doc):
	company = frappe.get_cached_doc("Company", doc.company)
	paid = doc.docstatus == 1
	lines = [_line(company.company_name, bold=True, size=2, align="c")]
	address = _company_address(doc.company)
	if address:
		lines.append(_line(address, align="c"))
	if company.tax_id:
		lines.append(_line(f"TRN: {company.tax_id}", align="c"))
	lines += [
		_line("TAX INVOICE" if paid else "BILL - NOT PAID", bold=True, align="c"),
		_divider(),
		_line(f"No: {doc.name}"),
		_line(f"Date: {format_datetime(doc.creation, 'dd MMM yyyy  HH:mm')}"),
		_line(f"Order: {doc.get('custom_ury_order_number') or '-'}  {ORDER_TYPE_LABELS.get(doc.order_type, doc.order_type or '')}".rstrip()),
	]
	comments = doc.get("custom_comments") or ""
	if comments.startswith(CURBSIDE_PREFIX):
		lines.append(_line(f"Car: {comments[len(CURBSIDE_PREFIX):]}"))
	elif doc.get("restaurant_table"):
		lines.append(_line(f"Table: {doc.restaurant_table}"))
	lines.append(_divider())
	for item in doc.items:
		lines.append(_columns(f"{flt(item.qty):g} x {item.item_name}", _money(item.amount)))
	lines.append(_divider())
	if flt(doc.discount_amount):
		lines.append(_columns("Discount", f"-{_money(doc.discount_amount)}"))
	lines.append(_columns("Total excl. VAT", _money(doc.net_total)))
	for tax in doc.taxes:
		lines.append(_columns(tax.description or "VAT", _money(tax.tax_amount_after_discount_amount)))
	total = doc.rounded_total or doc.grand_total
	lines.append(_columns(f"TOTAL {doc.currency}", _money(total), bold=True, size=2))
	if paid:
		lines.append(_divider())
		for payment in doc.payments:
			if flt(payment.amount):
				lines.append(_columns(payment.mode_of_payment, _money(payment.amount)))
		if flt(doc.change_amount):
			lines.append(_columns("Change", _money(doc.change_amount)))
	lines += [_divider(), _line("Thank you for choosing FryBird!", align="c")]
	return lines


def _company_address(company):
	name = frappe.db.get_value("Dynamic Link", {"link_doctype": "Company", "link_name": company, "parenttype": "Address"}, "parent")
	if not name:
		return ""
	address = frappe.db.get_value("Address", name, ["address_line1", "city"], as_dict=True)
	return ", ".join(filter(None, [address.address_line1, address.city]))


def _money(value):
	return f"{flt(value):,.2f}"


def _columns(left, right, bold=False, size=1):
	width = WIDTH // size
	left, right = _ascii(left), _ascii(right)
	if len(left) + len(right) + 1 > width:
		left = left[: width - len(right) - 1]
	return _line(left.ljust(width - len(right)) + right, bold=bold, size=size)


def _wrap(text, indent="", width=WIDTH):
	return textwrap.wrap(_ascii(text), width, subsequent_indent=indent, drop_whitespace=True) or [""]


def _divider():
	return _line("-" * WIDTH)


def _line(text, bold=False, size=1, align="l"):
	return {"t": _ascii(text), "b": bold, "s": size, "a": align}


def _ascii(text):
	"""Receipt printers' default code page can't show accents or smart quotes."""
	return unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
