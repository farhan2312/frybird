"""Print documents for the FryBird Android app on the counter terminal (see android/).

The server can't reach printers on the shop network, so the app collects kitchen tickets from here
and sends them to the kitchen printer itself. Layout lives here so it can change without a new app.

A print document is a list of lines: {"t": text, "b": bold, "s": 1, 2, 3 or 4 (normal, double, double height, double width), "a": "l", "c" or "r"}.
"""

import json
import textwrap
import unicodedata

import frappe
from frappe import _
from frappe.utils import add_to_date, flt, format_datetime, now_datetime

from ury.ury.api.self_ordering import CURBSIDE_PREFIX

PRINT_ROLE = "URY Print Agent"
PRINT_USER = "printer@frybird.ae"
TICKET_HEADER = "FRYBIRD AJMAN"
TICKET_ITEM_SIZE = 4  # double width at normal height, like the shop's old tickets
WIDTH = 48  # characters per line at normal size on 80mm paper
TICKET_ITEM_WIDTH = WIDTH // 2
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
	return [{"kots": [k.name for k in group], "lines": _ticket_lines(group)} for group in groups.values()]


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
	return invoice.order_type or "Take Away"


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
		_line(f"Order: {doc.get('custom_ury_order_number') or '-'}  {doc.order_type or ''}".rstrip()),
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
