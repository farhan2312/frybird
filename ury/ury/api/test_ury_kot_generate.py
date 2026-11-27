from frappe.tests.utils import FrappeTestCase

from ury.ury.api.ury_kot_generate import diff_order_items


def line(code, qty=1, comments=""):
	return {"item_code": code, "item_name": code, "qty": qty, "comments": comments}


class TestDiffOrderItems(FrappeTestCase):
	def test_same_item_with_new_comment_is_sent(self):
		# A second meal with Pepsi added to an order that already has one with 7 Up.
		before = [line("BURGER"), line("MEAL", comments="7 up")]
		added, cancelled = diff_order_items(before + [line("SANDO"), line("MEAL", comments="Pepsi")], before)
		self.assertEqual(added, [line("SANDO"), line("MEAL", comments="Pepsi")])
		self.assertEqual(cancelled, [])

	def test_unchanged_order_sends_nothing(self):
		order = [line("MEAL", comments="7 up"), line("MEAL", comments="Pepsi")]
		self.assertEqual(diff_order_items(order, order), ([], []))

	def test_quantity_change(self):
		self.assertEqual(diff_order_items([line("MEAL", 3)], [line("MEAL")]), ([line("MEAL", 2)], []))
		self.assertEqual(diff_order_items([line("MEAL")], [line("MEAL", 3)]), ([], [line("MEAL", 2)]))

	def test_split_lines_add_up(self):
		# Two separate lines of the same item count as one quantity.
		self.assertEqual(diff_order_items([line("MEAL", 2)], [line("MEAL"), line("MEAL")]), ([], []))

	def test_removed_line_is_cancelled(self):
		before = [line("MEAL", comments="7 up"), line("MEAL", comments="Pepsi")]
		self.assertEqual(diff_order_items(before[:1], before), ([], [line("MEAL", comments="Pepsi")]))

	def test_lost_note_is_not_a_cancel(self):
		# FB-00283: "Cut" burgers reloaded without the note, plus a Cola added.
		before = [line("BIGCHEESE", 4, "Cut"), line("SANDO", 2, "Cut"), line("FRIES")]
		after = [line("BIGCHEESE", 4), line("SANDO", 2), line("FRIES"), line("COLA")]
		self.assertEqual(diff_order_items(after, before), ([line("COLA")], []))

	def test_lost_note_with_more_quantity_sends_only_the_extra(self):
		added, cancelled = diff_order_items([line("FRIES", 3)], [line("FRIES", 2, "Cheese fries")])
		self.assertEqual((added, cancelled), ([line("FRIES", 1)], []))

	def test_new_note_on_sent_item_still_counts_as_new(self):
		# Adding a note to a line already sent stays a cancel plus a new line, so the kitchen sees the note.
		added, cancelled = diff_order_items([line("MEAL", comments="Pepsi")], [line("MEAL")])
		self.assertEqual((added, cancelled), ([line("MEAL", comments="Pepsi")], [line("MEAL")]))

