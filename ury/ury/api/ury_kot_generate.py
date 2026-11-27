import json

import frappe
from frappe.utils import flt
from ury.ury_pos.api import getBranch


# Load JSON data or return as is if it's already a Python dictionary
def load_json(data):
    if isinstance(data, str):
        return json.loads(data)
    return data


# Create a list of order items from a list of input items
def create_order_items(items):
    order_items = []
    for item in items:
        order_item = {
            "item_code": item.get("item", item.get("item_code")),
            "qty": item["qty"],
            "item_name": item["item_name"],
            "comments": item.get("comment", item.get("comments", "")),
        }
        order_items.append(order_item)
    return order_items


# Create a KOT (Kitchen Order Ticket) document
def create_kot_doc(
    invoice_id,
    customer,
    restaurant_table,
    items,
    kot_type,
    comments,
    pos_profile_id,
    kot_naming_series,
    production,
):
    pos_invoice = frappe.get_doc("POS Invoice", invoice_id)
    order_number = pos_invoice.custom_ury_order_number
    is_aggregator = 0
    if pos_invoice.order_type == "Aggregators":
        is_aggregator = 1
    kot_doc = frappe.get_doc(
        {
            "doctype": "URY KOT",
            "invoice": invoice_id,
            "restaurant_table": restaurant_table,
            "custom_merged_tables": pos_invoice.get("custom_merged_tables"),
            "customer_name": customer,
            "pos_profile": pos_profile_id,
            "comments": comments,
            "type": kot_type,
            "naming_series": kot_naming_series,
            "production": production,
            "aggregator_id":pos_invoice.custom_aggregator_id,
            "is_aggregator":is_aggregator,
            "order_no":order_number
        }
    )
    branch = getBranch()
    if restaurant_table:
        room = frappe.db.get_value("URY Table", restaurant_table, "restaurant_room")
        restaurant = frappe.db.get_value("URY Table", restaurant_table, "restaurant")
        menu = frappe.db.get_value("Menu for Room", {"room": room,"parent":restaurant}, "menu")
        
    else:
        menu = frappe.db.get_value("URY Restaurant", {"branch": branch}, "active_menu")

    for item in items:
        course = frappe.db.get_value("URY Menu Item", {"item": item["item_code"],"parent":menu}, "course")
        kot_doc.append(
            "kot_items",
            {
                "item": item["item_code"],
                "item_name": item["item_name"],
                "quantity": item["qty"],
                "comments": item["comments"],
                "course":course
            },
        )
    kot_doc.insert()
    kot_doc.submit()
    return kot_doc.name

# Function to get all production item groups for a given branch
def get_all_production_item_groups(branch):
    productions = frappe.db.get_all(
        "URY Production Unit", filters={"branch": branch}, fields=["name"]
    )
    if productions:
        all_production_item_groups = set()
        for production in productions:
            productionItemGroupslist = frappe.get_all(
                "URY Production Item Groups",
                fields=["item_group"],
                filters={
                    "parent": production.name,
                    "parenttype": "URY Production Unit",
                },
                order_by="idx",
            )
            productionItemGroups = [
                item_group.item_group for item_group in productionItemGroupslist
            ]
            all_production_item_groups.update(productionItemGroups)
        return all_production_item_groups


# Process items to create KOT documents
def process_items_for_kot(
    invoice_id,
    customer,
    restaurant_table,
    items,
    comments,
    pos_profile_id,
    kot_naming_series,
    kot_type,
):
    kot_items = create_order_items(items)
    pos_profile = frappe.get_doc("POS Profile", pos_profile_id)
    productions = frappe.db.get_all(
        "URY Production Unit", filters={"branch": pos_profile.branch}, fields=["name"], order_by="creation"
    )

    created_kot_names = []

    if productions:
        items_by_production = _split_by_production(productions, kot_items)
        for production in productions:
            production_items = items_by_production[production.name]

            if production_items:
                invoice_exist = frappe.db.exists(
                    "URY KOT",
                    {
                        "invoice": invoice_id,
                        "docstatus": 1,
                        "production": production.name,
                    },
                )
                if invoice_exist:
                    kot_type = "Order Modified"

                kot_name = create_kot_doc(
                    invoice_id,
                    customer,
                    restaurant_table,
                    production_items,
                    kot_type,
                    comments,
                    pos_profile_id,
                    kot_naming_series,
                    production.name,
                )
                created_kot_names.append(kot_name)
    else:
        frappe.throw(
            "Create URY Production unit against POS Profile: %s " % pos_profile.name
        )

    return created_kot_names


# Process items to create a cancel KOT document
def process_items_for_cancel_kot(
    invoice_id,
    customer,
    restaurant_table,
    items,
    comments,
    pos_profile_id,
    cancel_kot_naming_series,
    kot_type,
    invoiceItems,
):

    kot_items = create_order_items(items)
    pos_profile = frappe.get_doc("POS Profile", pos_profile_id)
    productions = frappe.db.get_all(
        "URY Production Unit", filters={"branch": pos_profile.branch}, fields=["name"], order_by="creation"
    )

    created_kot_names = []

    items_by_production = _split_by_production(productions, kot_items)
    for production in productions:
        production_items = items_by_production[production.name]

        if production_items:
            kot_name = create_cancel_kot_doc(
                invoice_id,
                restaurant_table,
                production_items,
                kot_type,
                customer,
                comments,
                pos_profile_id,
                cancel_kot_naming_series,
                invoiceItems,
                production.name,
            )
            created_kot_names.append(kot_name)

    return created_kot_names


# Create a cancel KOT document
def create_cancel_kot_doc(
    invoice_id,
    restaurant_table,
    cancel_items,
    kot_type,
    customer,
    comments,
    pos_profile_id,
    cancel_kot_naming_series,
    invoiceItems,
    production,
):
    pos_invoice = frappe.get_doc("POS Invoice", invoice_id)
    order_number = pos_invoice.custom_ury_order_number  
    is_aggregator = 0
    if pos_invoice.order_type == "Aggregators":
        is_aggregator = 1
    kot_list = frappe.db.get_list(
        "URY KOT",
        filters={
            "invoice": invoice_id,
            "type": ("in", ("New Order", "Order Modified")),
        },
        fields=("name"),
    )

    # Find original KOTs related to the cancel items
    original_kots = []
    for cancelItem in cancel_items:
        for kot in kot_list:
            kot_doc = frappe.get_doc("URY KOT", kot.name)
            kot_cancel_items = kot_doc.kot_items
            itemCheckFlag = False
            for kotItem in kot_cancel_items:
                if cancelItem["item_code"] == kotItem.item:
                    itemCheckFlag = True
            if itemCheckFlag:
                original_kots.append(kot_doc.name)
                break

    # Remove duplicate KOT names and join them into a single string
    set_kots = [*set(original_kots)]
    set_kots = ",".join(set_kots)
    kot_cancel_doc = frappe.get_doc(
        {
            "doctype": "URY KOT",
            "naming_series": cancel_kot_naming_series,
            "original_kot": set_kots,
            "restaurant_table": restaurant_table,
            "customer_name": customer,
            "type": kot_type,
            "invoice": invoice_id,
            "pos_profile": pos_profile_id,
            "comments": comments,
            "production": production,
            "is_aggregator":is_aggregator,
            "order_no":order_number
        }
    )

    branch = getBranch()
    if restaurant_table:
        room = frappe.db.get_value("URY Table", restaurant_table, "restaurant_room")
        restaurant = frappe.db.get_value("URY Table", restaurant_table, "restaurant")
        menu = frappe.db.get_value("Menu for Room", {"room": room,"parent":restaurant}, "menu")
        
    else:
        menu = frappe.db.get_value("URY Restaurant", {"branch": branch}, "active_menu")
    for cancelItem in cancel_items:
        course = frappe.db.get_value("URY Menu Item", {"item": cancelItem["item_code"],"parent":menu}, "course")
        ordered = sum(flt(item["qty"]) for item in invoiceItems if _line_key(item) == _line_key(cancelItem))
        kot_cancel_doc.append(
            "kot_items",
            {
                "item": cancelItem["item_code"],
                "item_name": cancelItem["item_name"],
                "cancelled_qty": abs(int(flt(cancelItem["qty"]))),
                "quantity": _whole(ordered or flt(cancelItem["qty"])),
                "comments": cancelItem["comments"],
                "course":course
            },
        )

    kot_cancel_doc.insert()
    kot_cancel_doc.submit()
    return kot_cancel_doc.name


# Whitelisted function to handle KOT entry
@frappe.whitelist()
def kot_execute(
    invoice_id,
    customer,
    restaurant_table=None,
    current_items=[],
    previous_items=[],
    comments=None,
):
    from frappe import _

    pos_invoice = frappe.get_doc("POS Invoice", invoice_id)
    if not frappe.has_permission("POS Invoice", "write", doc=pos_invoice):
        frappe.throw(_("Not permitted to execute KOT for this invoice"), frappe.PermissionError)

    current_items = load_json(current_items)
    previous_items = load_json(previous_items)
    new_invoice_items_array = create_order_items(previous_items)
    new_Order_items_array = create_order_items(current_items)

    positive_qty_items, total_cancel_items = diff_order_items(new_Order_items_array, new_invoice_items_array)

    pos_profile_id = pos_invoice.pos_profile
    pos_profile = frappe.get_doc("POS Profile", pos_profile_id)
    kot_naming_series = pos_profile.custom_kot_naming_series
    if kot_naming_series:
        cancel_kot_naming_series = "CNCL-" + kot_naming_series
    else:
        frappe.throw(
            "KOT Naming Series is mandatory for the auto creation of KOT.Ensure it is configured in the POS Profile: %s"
            % pos_profile.name
        )

    from ury.ury.api.ury_waiter_print import print_combined_waiter_order_slip

    created_kot_names = []

    if positive_qty_items:
        created_kot_names.extend(
            process_items_for_kot(
                invoice_id,
                customer,
                restaurant_table,
                positive_qty_items,
                comments,
                pos_profile_id,
                kot_naming_series,
                "New Order",
            )
        )
    if total_cancel_items:
        created_kot_names.extend(
            process_items_for_cancel_kot(
                invoice_id,
                customer,
                restaurant_table,
                total_cancel_items,
                comments,
                pos_profile_id,
                cancel_kot_naming_series,
                "Partially cancelled",
                new_invoice_items_array,
            )
        )

    if created_kot_names:
        print_combined_waiter_order_slip(invoice_id, created_kot_names, restaurant_table)


def _line_key(item):
    return (item["item_code"], (item.get("comments") or "").strip())


def diff_order_items(current_items, previous_items):
    """What to send to the kitchen when an order is saved: (added, cancelled).

    Lines are matched by item and comment, with quantities added up, so the same item ordered again with
    a different comment (a second meal with Pepsi instead of 7 Up, another spice level) counts as new and
    is never mistaken for the line already sent."""
    def totals(items):
        lines = {}
        for item in items:
            key = _line_key(item)
            if key in lines:
                lines[key]["qty"] = flt(lines[key]["qty"]) + flt(item["qty"])
            else:
                lines[key] = dict(item, qty=flt(item["qty"]), comments=key[1])
        return lines

    current, previous = totals(current_items), totals(previous_items)
    added, cancelled = [], []
    for key, item in current.items():
        change = item["qty"] - (previous[key]["qty"] if key in previous else 0)
        if change > 0:
            added.append(dict(item, qty=_whole(change)))
    for key, item in previous.items():
        change = item["qty"] - (current[key]["qty"] if key in current else 0)
        if change > 0:
            cancelled.append(dict(item, qty=_whole(change)))

    # A line that comes back with its note missing is the line already sent, not a cancel plus a new
    # item: a screen that loses notes on reload must not send the kitchen a false "CANCELLED" ticket.
    for new in added:
        if new["comments"]:
            continue
        for old in cancelled:
            if old["item_code"] == new["item_code"] and old["comments"] and flt(new["qty"]) > 0 and flt(old["qty"]) > 0:
                same = min(flt(new["qty"]), flt(old["qty"]))
                new["qty"], old["qty"] = _whole(flt(new["qty"]) - same), _whole(flt(old["qty"]) - same)
    return [i for i in added if flt(i["qty"]) > 0], [i for i in cancelled if flt(i["qty"]) > 0]


def _whole(qty):
    return int(qty) if flt(qty).is_integer() else qty


# Compare two arrays and return the items that are different (no longer used by kot_execute; see diff_order_items)
def compare_two_array(array_1, array_2):
    finalarray = []
    for index, x in enumerate(array_1):
        a = list(
            filter(
                lambda y: y["item_code"] == x["item_code"] and y["qty"] == x["qty"],
                array_2,
            )
        )
        if len(a) == 0:
            b = list(filter(lambda z: z["item_code"] == x["item_code"], array_2))
            for qtb in b:
                x["qty"] = int(x["qty"]) - int(qtb["qty"])
            finalarray.append(x)
    return finalarray


# Get the items that have been removed from the second array compared to the first array
def get_removed_items(array_1, array_2):
    removed_objects = [
        obj
        for obj in array_1
        if obj["item_code"] not in [x["item_code"] for x in array_2]
    ]
    return removed_objects


def _split_by_production(productions, kot_items):
    """Items per production unit. Every item goes to the kitchen: one whose item group no station
    makes (meal upgrade, dips, a new group) goes on the first station's ticket instead of being dropped."""
    if not productions:
        return {}
    station_of_group = {}
    for production in productions:
        for row in frappe.get_all("URY Production Item Groups", fields=["item_group"],
                                  filters={"parent": production.name, "parenttype": "URY Production Unit"}):
            station_of_group.setdefault(row.item_group, production.name)
    split = {production.name: [] for production in productions}
    for item in kot_items:
        group = frappe.db.get_value("Item", item["item_code"], "item_group")
        split[station_of_group.get(group, productions[0].name)].append(item)
    return split
