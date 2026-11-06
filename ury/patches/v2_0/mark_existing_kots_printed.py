import frappe


def execute():
	# Only tickets created after the print app arrives should reach the kitchen printer.
	frappe.db.sql("update `tabURY KOT` set kitchen_printed = 1")
