import random
import re
import string
import xml.etree.ElementTree as ET

import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.doctype.payment_order.payment_order import PaymentOrder
from erpnext.accounts.utils import get_account_currency
from frappe import _, bold, parse_json
from frappe.utils import cstr, getdate


class BankPaymentOrder(PaymentOrder):
	def on_submit(self):
		if self.payment_order_type not in [
			"Payment Entry",
			"Payroll Entry",
			"Journal Entry",
		]:
			# make_payment_entries(self)
			frappe.db.set_value("Payment Order", self.name, "status", "Pending")

			for ref in self.references:
				if hasattr(ref, "payment_request"):
					frappe.db.set_value(
						"Payment Request",
						ref.payment_request,
						"status",
						"Payment Ordered",
					)

	@frappe.whitelist()
	def get_party_summary(self):
		summarise_payment_based_on = frappe.get_single(
			"Bank Integration Settings"
		).summarise_payment_based_on

		def _get_unique_key(ref=None, summarise_field=False):
			if summarise_payment_based_on == "Party":
				if summarise_field:
					return (
						"party_type",
						"party",
						"bank_account",
						"account",
						"cost_center",
						"project",
						"tax_withholding_category",
						"reference_doctype",
					)

				return (
					ref.party_type,
					ref.party,
					ref.bank_account,
					ref.account,
					ref.cost_center,
					ref.project,
					ref.tax_withholding_category,
					ref.reference_doctype,
				)

			elif summarise_payment_based_on == "Voucher":
				if summarise_field:
					return (
						"party_type",
						"party",
						"reference_doctype",
						"reference_name",
						"bank_account",
						"account",
						"cost_center",
						"project",
						"tax_withholding_category",
					)

				return (
					ref.party_type,
					ref.party,
					ref.reference_doctype,
					ref.reference_name,
					ref.bank_account,
					ref.account,
					ref.cost_center,
					ref.project,
					ref.tax_withholding_category,
				)

		summary = {}
		remarks_list = {}
		for ref in self.references:
			key = _get_unique_key(ref)
			remark = ref.remarks if ref.remarks else ""

			if key in summary:
				summary[key] += ref.amount
			else:
				summary[key] = ref.amount
				remarks_list[key] = remark

		result = []
		for key, val in summary.items():
			summary_line_item = {
				k: v for k, v in zip(_get_unique_key(summarise_field=True), key)
			}
			summary_line_item["amount"] = val
			summary_line_item["remarks"] = remarks_list[key]
			if summarise_payment_based_on == "Party":
				summary_line_item["is_party_wise"] = 1
			else:
				summary_line_item["is_party_wise"] = 0

			result.append(summary_line_item)

		for row in result:
			party_bank = frappe.db.get_value(
				"Bank Account", row["bank_account"], "bank"
			)
			company_bank = frappe.db.get_value(
				"Bank Account", self.company_bank_account, "bank"
			)
			row["mode_of_transfer"] = None
			if party_bank == company_bank:
				mode_of_transfer = frappe.db.get_value(
					"Mode of Transfer", {"is_bank_specific": 1, "bank": party_bank}
				)
				if mode_of_transfer:
					row["mode_of_transfer"] = mode_of_transfer
			else:
				mot = frappe.db.get_value(
					"Mode of Transfer",
					{
						"minimum_limit": ["<=", row["amount"]],
						"maximum_limit": [">", row["amount"]],
						"is_bank_specific": 0,
					},
					order_by="priority asc",
				)
				if mot:
					row["mode_of_transfer"] = mot

		return result

	@frappe.whitelist()
	def export_pain_file(self):
		order_xml = self.get_formated_data()
		count = frappe.db.count(
			"File",
			{
				"attached_to_doctype": self.doctype,
				"attached_to_name": self.name,
				"file_name": ["like", "%{}%".format(self.name)],
			},
		)
		xml_filename = self.name + f"({count}).xml" if count else self.name + ".xml"
		_file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": xml_filename,
				"attached_to_doctype": self.doctype,
				"attached_to_name": self.name,
				"content": order_xml,
				"is_private": False,
			}
		)
		_file.save(ignore_permissions=True)
		if _file:
			frappe.msgprint(_("File exported successfully."))

	def get_formated_data(self):
		def dict_to_xml(tag, data, namespaces={}):
			"""Convert a dictionary to an XML element."""
			if namespaces:
				element = ET.Element(
					tag, {f"{prefix}": uri for prefix, uri in namespaces.items()}
				)
			else:
				element = ET.Element(tag)

			for key, value in data.items():
				if isinstance(value, dict):
					child = dict_to_xml(key, value)
					element.append(child)
				elif isinstance(value, list):
					for val in value:
						if isinstance(val, dict):
							child = dict_to_xml(key, val)
							element.append(child)
						elif isinstance(val, str):
							child = ET.SubElement(element, key)
							child.text = cstr(val)
				else:
					child = ET.SubElement(element, key)
					child.text = cstr(value)

			return element

		json_data = self.get_json_data()
		namespaces = {
			"xmlns": "http://www.six-interbank-clearing.com/de/pain.001.001.03.ch.02.xsd",
			"xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
			"xsi:schemaLocation": "http://www.six-interbank-clearing.com/de/pain.001.001.03.ch.02.xsd pain.001.001.03.ch.02.xsd",
		}

		root = dict_to_xml("Document", json_data, namespaces)

		return ET.tostring(root, encoding="utf-8", short_empty_elements=False).decode(
			"utf-8"
		)

	def get_id(self, length, text=""):
		text = "".join(re.findall(r"[0-9a-zA-Z]", text))
		idd = "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
		return text + idd

	def get_json_data(self):
		# company_bank
		c_bank = frappe.get_doc("Bank Account", self.company_bank_account)
		return {
			"CstmrCdtTrfInitn": {
				"GrpHdr": {
					"MsgId": self.get_id(20, self.name),
					"CreDtTm": getdate().strftime("%Y-%m-%dT%H:%M:%S%z"),
					"NbOfTxs": cstr(len(self.summary)),
					"CtrlSum": cstr(self.total),
					"InitgPty": {
						"Nm": self.company,
						"CtctDtls": {
							"Nm": c_bank.account_name,
							"Othr": "2023.205 ex. Version",
						},
					},
				},
				"PmtInf": {
					"PmtInfId": self.get_id(25),
					"PmtMtd": "TRF",
					"BtchBookg": "true",
					"NbOfTxs": cstr(len(self.summary)),
					"PmtTpInf": {"CtgyPurp": {"Cd": self.get_purpose_code()}},
					"ReqdExctnDt": getdate().strftime("%Y-%m-%d"),
					"Dbtr": {"Nm": c_bank.account_name},
					"DbtrAcct": {
						"Id": {
							"IBAN": c_bank.iban.replace(" ", "") if c_bank.iban else ""
						},
						"Tp": {"Prtry": "CND"},
					},
					"DbtrAgt": {"FinInstnId": {"BIC": c_bank.branch_code}},
					"CdtTrfTxInf": list(self.get_payment_details_list()),
				},
			}
		}

	def get_purpose_code(self):
		if self.summary:
			if self.summary[0].party_type == "Supplier":
				return "SUPP"
			elif self.summary[0].party_type == "Employee":
				return "SALA"

	def get_payment_details_list(self):
		for data in self.summary:
			if data.party_type == "Employee":
				party_field = "employee_name"
			elif data.party_type == "Supplier":
				party_field = "supplier_name"
			else:
				return []

			currency = frappe.db.get_value(
				data.party_type, data.party, "default_currency"
			) or frappe.db.get_value("Company", self.company, "default_currency")

			# party_bank
			p_bank = frappe.get_doc("Bank Account", data.bank_account)

			address_name = frappe.get_doc(
				"Dynamic Link",
				{"link_doctype": "Bank Account", "link_name": data.bank_account},
				"name",
			)
			if not address_name:
				frappe.throw(
					_(
						f"Address Not found for given bank account({bold(data.bank_account)})"
					)
				)

			p_address = frappe.get_doc("Address", address_name)

			address_line = p_address.address_line1.split(",")
			yield {
				"PmtId": {
					"InstrId": self.get_id(20),
					"EndToEndId": self.get_id(20),
				},
				"Amt": {"InstdAmt": {"Ccy": currency, "value": data.amount}},
				"ChrgBr": "SHAR",
				"CdtrAgt": {"FinInstnId": {"BIC": p_bank.branch_code}},
				"Cdtr": {
					"Nm": frappe.db.get_value(data.party_type, data.party, party_field),
					"PstlAdr": {
						"StrtNm": address_line[1] if address_line[1:2] else "",
						"BldgNb": address_line[0] if address_line[0:1] else "",
						"PstCd": p_address.pincode,
						"TwnNm": p_address.city,
						"Ctry": frappe.get_value("Country", p_address.country, "code"),
					},
				},
				"CdtrAcct": {"Id": {"IBAN": p_bank.iban}},
				"RmtInf": {"Ustrd": data.remarks},
			}


@frappe.whitelist()
def update_payment_status(data):
	if isinstance(data, str) or isinstance(data, dict):
		data = parse_json(data)

	success_count = 0
	for i, d in enumerate(data, start=1):
		d = parse_json(d)
		if d.row_name:
			if d.status == "Processed":
				if not d.reference_number or not d.payment_date:
					frappe.throw(
						"The status can be updated to 'Processed' only if the Payment Date and Payment Reference Number are provided."
					)

				frappe.db.set_value(
					"Payment Order Summary",
					d.row_name,
					{
						"payment_status": "Processed",
						"reference_number": d.reference_number,
						"payment_date": d.payment_date,
						"payment_initiated": 1,
					},
				)
				if d.payment_entry:
					frappe.db.set_value(
						"Payment Entry",
						d.payment_entry,
						{
							"reference_no": d.reference_number,
							"reference_date": d.payment_date
						},
					)
				else:
					payment_order = frappe.get_doc("Payment Order", d.payment_order)
					make_payment_entries(payment_order, d)

				success_count += 1
			elif d.status == "Failed":
				frappe.db.set_value(
					"Payment Order Summary",
					d.row_name,
					{"payment_status": "Failed", "payment_initiated": 1},
				)

				if d.payment_entry:
					payment_entry_doc = frappe.get_doc("Payment Entry", d.payment_entry)
					if payment_entry_doc.docstatus == 1:
						payment_entry_doc.cancel()

				process_payment_requests(d.row_name)

				success_count += 1
	if success_count:
		frappe.msgprint(_(f"{success_count} payment(s) updated"))


@frappe.whitelist()
def make_payment_entries(payment_order_doc, summary_doc: dict | str = None):
	"""create entry"""
	summary_doc = parse_json(summary_doc or {})

	frappe.flags.ignore_account_permission = True

	for row in payment_order_doc.summary:
		if summary_doc and summary_doc.row_name != row.name:
			continue

		pe = frappe.new_doc("Payment Entry")
		pe.payment_type = "Pay"
		pe.company = payment_order_doc.company
		pe.cost_center = row.cost_center
		pe.project = row.project
		pe.posting_date = getdate()
		pe.mode_of_payment = "Wire Transfer"
		pe.party_type = row.party_type
		pe.party = row.party
		pe.bank_account = payment_order_doc.company_bank_account
		pe.party_bank_account = row.bank_account
		if pe.party_type == "Supplier":
			pe.ensure_supplier_is_not_blocked()
		pe.payment_order = payment_order_doc.name

		pe.paid_from = payment_order_doc.account
		if row.account:
			pe.paid_to = row.account
		pe.paid_from_account_currency = get_account_currency(payment_order_doc.account)
		pe.paid_to_account_currency = get_account_currency(row.account)
		pe.paid_amount = row.amount
		pe.received_amount = row.amount
		pe.letter_head = frappe.db.get_value("Letter Head", {"is_default": 1}, "name")

		for dimension in get_accounting_dimensions():
			pe.update({dimension: payment_order_doc.get(dimension, "")})

		if row.tax_withholding_category:
			net_total = 0

			for reference in payment_order_doc.references:
				if (
					reference.party_type == row.party_type
					and reference.party == row.party
					and reference.cost_center == row.cost_center
					and reference.project == row.project
					and reference.bank_account == row.bank_account
					and reference.account == row.account
					and reference.tax_withholding_category
					== row.tax_withholding_category
					and reference.reference_doctype == row.reference_doctype
				):
					net_total += frappe.db.get_value(
						"Payment Request", reference.payment_request, "net_total"
					)
			pe.paid_amount = net_total
			pe.received_amount = net_total
			pe.apply_tax_withholding_amount = 1
			pe.tax_withholding_category = row.tax_withholding_category

		for reference in payment_order_doc.references:
			if not reference.is_adhoc:
				filter_condition = (
					reference.party_type == row.party_type
					and reference.party == row.party
					and reference.cost_center == row.cost_center
					and reference.project == row.project
					and reference.bank_account == row.bank_account
					and reference.account == row.account
					and reference.tax_withholding_category
					== row.tax_withholding_category
					and reference.reference_doctype == row.reference_doctype
				)

				if not payment_order_doc.is_party_wise:
					filter_condition = filter_condition and (
						reference.reference_doctype == row.reference_doctype
						and reference.reference_name == row.reference_name
					)

				if filter_condition:
					reference_amount = frappe.db.get_value(
						"Payment Request", reference.payment_request, "net_total"
					)
					payment_term = ""
					try:
						payment_term = frappe.db.get_value(
							"Payment Request", reference.payment_request, "payment_term"
						)

						if not payment_term:
							if template := frappe.db.get_value(
								reference.reference_doctype,
								reference.reference_name,
								"payment_terms_template",
							):
								splited_invoice_rows = get_split_invoice_rows(
									frappe._dict(
										{"voucher_no": reference.reference_name}
									),
									template,
									exc_rates={
										reference.reference_name: frappe.get_doc(
											"Purchase Invoice", reference.reference_name
										)
									},
								)

								is_term_applied = frappe.db.get_value(
									"Payment Terms Template",
									template,
									"allocate_payment_based_on_payment_terms",
								)

								if splited_invoice_rows and is_term_applied:
									term_row = 0
									while reference_amount > 0:
										term_paid = (
											frappe.get_value(
												"Payment Entry Reference",
												{
													"reference_doctype": reference.reference_doctype,
													"reference_name": reference.reference_name,
													"payment_term": splited_invoice_rows[
														term_row
													].get("payment_term"),
													"docstatus": 1,
												},
												"sum(allocated_amount)",
											)
											or 0
										)

										per = (
											frappe.db.get_value(
												"Payment Term",
												splited_invoice_rows[term_row].get(
													"payment_term"
												),
												"invoice_portion",
											)
											/ 100
										)
										invoice_amount = frappe.db.get_value(
											reference.reference_doctype,
											reference.reference_name,
											"grand_total",
										)
										to_be_pay = per * invoice_amount

										if (reference_amount + term_paid) <= to_be_pay:
											paid_amount = reference_amount
											reference_amount -= paid_amount
										else:
											paid_amount = to_be_pay - term_paid
											reference_amount -= paid_amount

										if paid_amount:
											pe.append(
												"references",
												{
													"reference_doctype": reference.reference_doctype,
													"reference_name": reference.reference_name,
													"total_amount": invoice_amount,
													"allocated_amount": paid_amount,
													"payment_term": splited_invoice_rows[
														term_row
													].get("payment_term"),
												},
											)
										term_row += 1
								else:
									pe.append(
										"references",
										{
											"reference_doctype": reference.reference_doctype,
											"reference_name": reference.reference_name,
											"total_amount": reference_amount,
											"allocated_amount": reference_amount,
										},
									)
							else:
								pe.append(
									"references",
									{
										"reference_doctype": reference.reference_doctype,
										"reference_name": reference.reference_name,
										"total_amount": reference_amount,
										"allocated_amount": reference_amount,
									},
								)
						else:
							pe.append(
								"references",
								{
									"reference_doctype": reference.reference_doctype,
									"reference_name": reference.reference_name,
									"total_amount": reference_amount,
									"allocated_amount": reference_amount,
									"payment_term": payment_term,
								},
							)
					except:
						frappe.log_error(
							"Error in Payment Terms Template", frappe.get_traceback()
						)

		pe.update(
			{
				"reference_no": summary_doc.reference_number or payment_order_doc.name,
				"reference_date": summary_doc.payment_date or getdate(),
				"remarks": "Bank Payment Entry from Payment Order - {0}".format(
					payment_order_doc.name
				),
			}
		)

		pe.setup_party_account_field()
		pe.set_missing_values()
		pe.validate()
		group_by_invoices(pe)

		pe.insert(ignore_permissions=True, ignore_mandatory=True)
		if frappe.get_single("Bank Integration Settings").submit_payment_entry:
			pe.submit()

		row.db_set("payment_entry", pe.name)


def group_by_invoices(self):
	grouped_references = {}
	if self.references:
		for ref in self.references:
			key = (ref.reference_name, ref.reference_doctype, ref.payment_term)
			if key not in grouped_references:
				grouped_references[key] = ref
			else:
				grouped_references[key].allocated_amount += ref.allocated_amount

		self.references = list(grouped_references.values())

def process_payment_requests(payment_order_summary):
	pos = frappe.get_doc("Payment Order Summary", payment_order_summary)
	payment_order_doc = frappe.get_doc("Payment Order", pos.parent)

	key = (
		pos.party_type, pos.party, pos.bank_account, pos.account, 
		pos.cost_center, pos.project, pos.tax_withholding_category, 
		pos.reference_doctype
	)

	failed_prs = []
	for ref in payment_order_doc.references:
		ref_key = (
			ref.party_type, ref.party, ref.bank_account, ref.account,
			ref.cost_center, ref.project, ref.tax_withholding_category, 
			ref.reference_doctype
		)

		if key == ref_key:
			failed_prs.append(ref.payment_request)
	
	for pr in failed_prs:
		pr_doc = frappe.get_doc("Payment Request", pr)
		if pr_doc.docstatus == 1:
			pr_doc.check_if_payment_entry_exists()
			pr_doc.set_as_cancelled()
			pr_doc.db_set("docstatus", 2)