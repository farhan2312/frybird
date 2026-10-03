"""A restaurant-manager login for showing FryBird to someone (POS, captain, kitchen display, admin, QR codes)
without handing out Administrator.

    from ury.setup.demo_user import create_demo_user
    create_demo_user("demo@frybird.test", "FryBird Demo", password)
"""

import frappe

ROLES = ["URY Manager", "URY Cashier", "URY Captain", "Sales User", "Accounts User", "Stock User"]
BRANCH = "FryBird Whitehall"
PROFILE = "FryBird POS"


def create_demo_user(email, full_name, password, branch=BRANCH, pos_profile=PROFILE):
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
	else:
		first, _, last = full_name.partition(" ")
		user = frappe.get_doc({"doctype": "User", "email": email, "first_name": first, "last_name": last,
							   "user_type": "System User", "send_welcome_email": 0})
		user.insert(ignore_permissions=True)
	user.enabled = 1
	user.new_password = password
	for role in ROLES:
		if frappe.db.exists("Role", role) and role not in [r.role for r in user.roles]:
			user.append("roles", {"role": role})
	user.flags.ignore_password_policy = True
	user.save(ignore_permissions=True)

	# URY resolves the user's restaurant from the branch's user list
	branch_doc = frappe.get_doc("Branch", branch)
	if not any(r.user == email for r in branch_doc.user):
		branch_doc.append("user", {"user": email})
		branch_doc.save(ignore_permissions=True)

	profile = frappe.get_doc("POS Profile", pos_profile)
	if not any(r.user == email for r in profile.applicable_for_users):
		profile.append("applicable_for_users", {"user": email})
		profile.save(ignore_permissions=True)

	frappe.db.commit()
	return email
