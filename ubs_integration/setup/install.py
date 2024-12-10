import click
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import delete_property_setter
from frappe import make_property_setter


def after_install():
	toggle_payment_request_creation(True)
	make_custom_fields()
	create_property_setter()


def before_uninstall():
	delete_custom_fields()
	toggle_payment_request_creation(False)
	delete_propert_setters()


def make_custom_fields():
	create_payment_request_tax_fields()
	create_payment_order_custom_fields()

def create_property_setter():
	create_payment_request_property_setter()

def delete_propert_setters():
    delete_payment_request_property_setter()

def toggle_payment_request_creation(allow=True):
	click.secho(
		"* {} Payment Request Creation...".format("Enabling" if allow else "Disabling")
	)
	frappe.db.set_value(
		"DocType", "Payment Request", {"in_create": not allow, "track_changes": allow}
	)


def create_payment_request_tax_fields():
	click.secho("* Installing Tax Custom Fields in Payment Request")
	fields = {
		"Payment Request": [
			{
				"label": "Payment Type",
				"fieldname": "payment_type",
				"fieldtype": "Link",
				"options": "Payment Type",
				"depends_on": "eval:doc.apply_tax_withholding_amount",
				"mandatory_depends_on": "eval:doc.mode_of_payment == 'Wire Transfer' && doc.reference_doctype != 'Purchase Invoice' && doc.payment_request_type == 'Outward'",
				"insert_after": "mode_of_payment",
			},
			{
				"label": "Is Adhoc",
				"fieldname": "is_adhoc",
				"fieldtype": "Check",
				"depends_on": "eval:doc.mode_of_payment == 'Wire Transfer' && doc.payment_request_type ==  'Outward'",
				"insert_after": "payment_type",
			},
			{
				"label": "Net Total",
				"fieldname": "net_total",
				"fieldtype": "Currency",
				"insert_after": "transaction_details",
			},
			{
				"label": "Taxes Deducted",
				"fieldname": "taxes_deducted",
				"fieldtype": "Currency",
				"depends_on": "eval:doc.tax_withholding_category",
				"insert_after": "net_total",
				"read_only": 1
			},
			{
				"label": "Apply Tax Withholding Amount",
				"fieldname": "apply_tax_withholding_amount",
				"fieldtype": "Check",
				"depends_on": "eval:doc.party_type == 'Supplier' && doc.reference_doctype != 'Purchase Invoice' && doc.payment_request_type == 'Outward'",
				"insert_after": "currency",
			},
			{
				"label": "Tax Withholding Category",
				"fieldname": "tax_withholding_category",
				"fieldtype": "Link",
				"options": "Tax Withholding Category",
				"depends_on": "eval:doc.apply_tax_withholding_amount",
				"insert_after": "apply_tax_withholding_amount",
			},
			{
				"label": "Payment Term",
				"fieldname": "payment_term",
				"fieldtype": "Link",
				"options": "Payment Term",
				"depends_on": "eval:doc.apply_tax_withholding_amount",
				"insert_after": "payment_order",
			},
			{"label": "Remarks", "fieldname": "remarks", "fieldtype": "Small Text"},
		]
	}
	create_custom_fields(fields)


def delete_custom_fields():
	fieldnames = {
		"Payment Request": [
			"payment_type",
			"is_adhoc",
			"net_total",
			"taxes_deducted",
			"apply_tax_withholding_amount",
			"tax_withholding_category",
			"payment_term",
		]
	}

	for doctype, fieldnames in fieldnames.items():
		click.secho(f"* Uninstalling Custom Fields from {doctype}")
		for fieldname in fieldnames:
			frappe.db.delete("Custom Field", {"name": f"{doctype}-" + fieldname})

		frappe.clear_cache(doctype=doctype)


properties = [{
		"doctype_or_field": "DocField",
		"doctype": "Payment Request",
		"fieldname": "grand_total",
		"property": "read_only",
		"property_type": "Check",
		"value": 1,
	}]

def create_payment_request_property_setter():
	for _property in properties:
		click.echo(f'* Updating {_property.get("doctype", "")} Property')
		make_property_setter(_property)


def delete_payment_request_property_setter():
    data = [(_property.get("doctype", ""), _property.get("property", ""), _property.get("fieldname", "")) for _property in properties]
    for doctype, property, fieldname in data:
        click.echo(f'* Updating {doctype} Property')
        delete_property_setter(doctype, property, fieldname)