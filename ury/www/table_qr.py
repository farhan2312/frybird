"""Printable QR codes for customer self-ordering (/order): one per table plus a pickup code.

Staff-only. Customers scan a code and land on /order?t=<signed token> for that table.
Use ?base=http://<pc-lan-ip>:8000 when phones reach the server on a different address than this browser.
"""

import io

import frappe
import pyqrcode
from frappe import _

from ury.ury.api.self_ordering import generate_qr_token

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=" + frappe.utils.quote(frappe.request.full_path)
		raise frappe.Redirect
	if not frappe.has_permission("URY Self Ordering Profile", "write"):
		frappe.throw(_("Only restaurant managers can print ordering QR codes"), frappe.PermissionError)

	profiles = frappe.get_all("URY Self Ordering Profile", {"enabled": 1}, ["name", "branch", "restaurant"], order_by="name")
	if not profiles:
		frappe.throw(_("Set up a URY Self Ordering Profile first"))
	selected = frappe.form_dict.get("profile") or profiles[0].name
	profile = next((p for p in profiles if p.name == selected), profiles[0])

	base = (frappe.form_dict.get("base") or _request_base()).rstrip("/")
	tables = frappe.get_all("URY Table", {"branch": profile.branch, "is_take_away": 0},
							["name", "restaurant_room", "no_of_seats"], order_by="restaurant_room, name")

	cards = []
	for t in tables:
		cards.append(_card(base, profile.name, t.name, f"Table {t.name}", t.restaurant_room))
	cards.append(_card(base, profile.name, None, "Pickup", "Order ahead, collect at the counter"))

	context.update({
		"title": _("Table QR codes"), "profiles": profiles, "profile": profile, "base": base,
		"cards": cards, "no_breadcrumbs": 1, "show_sidebar": 0,
	})
	return context


def _request_base():
	"""The address this page was opened on (works behind nginx / tunnels; get_url() adds the dev port)."""
	scheme = frappe.get_request_header("X-Forwarded-Proto") or frappe.request.scheme
	host = frappe.get_request_header("X-Forwarded-Host") or frappe.request.host
	return f"{scheme}://{host}"


def _card(base, profile, table, label, sublabel):
	url = f"{base}/order?t={generate_qr_token(profile, table)}"
	buf = io.BytesIO()
	pyqrcode.create(url, error="M").svg(buf, scale=6, quiet_zone=2, xmldecl=False, svgns=True, omithw=True)
	return {"label": label, "sublabel": sublabel, "url": url, "svg": buf.getvalue().decode()}
