import click
import frappe

from ury.setup_customizations import after_install as setup


def after_install():
    try:
        print("Setting up FryBird POS (URY)...")
        setup()
        set_frybird_branding()

        click.secho("Thank you for installing FryBird POS (powered by URY)!", fg="green")


    except Exception as e:
        print(f"Error during installation: {e}")
        pass


def set_frybird_branding():
    """Brand the Frappe login page, navbar and browser tab as FryBird."""
    logo = "/assets/ury/Images/frybird.png"
    favicon = "/assets/ury/pos/frybird.ico"

    website = frappe.get_single("Website Settings")
    website.app_name = "FryBird"
    website.app_logo = logo
    website.splash_image = "/assets/ury/Images/frybird-logo.jpg"
    website.favicon = favicon
    website.save(ignore_permissions=True)

    frappe.db.set_single_value("System Settings", "app_name", "FryBird")
    frappe.db.set_single_value("Navbar Settings", "app_logo", logo)
    frappe.clear_cache()
