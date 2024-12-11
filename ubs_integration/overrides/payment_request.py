import frappe
from erpnext.accounts.doctype.payment_request.payment_request import (
	PaymentRequest
)
from erpnext.accounts.doctype.tax_withholding_category.tax_withholding_category import (
	get_party_tax_withholding_details,
)
from frappe.utils.data import flt

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)


class BankPaymentRequest(PaymentRequest):
	def validate(self):
		if not self.net_total:
			self.net_total = self.grand_total
		if (
			self.apply_tax_withholding_amount
			and self.tax_withholding_category
			and self.payment_request_type == "Outward"
		):
			tds_amount = self.calculate_pr_tds(self.net_total)

			self.taxes_deducted = tds_amount
			self.grand_total = self.net_total - self.taxes_deducted
		else:
			if self.net_total and not self.grand_total:
				self.grand_total = self.net_total
			if (
				self.grand_total
				and self.net_total != self.grand_total
				and not self.apply_tax_withholding_amount
			):
				self.grand_total = self.net_total

		if not self.is_adhoc:
			super().validate()
		else:
			if self.get("__islocal"):
				self.status = "Draft"
			if self.reference_doctype or self.reference_name:
				frappe.throw("Payments with references cannot be marked as ad-hoc")

		if self.remarks:
			self.remarks = self.remarks[:48]

		self.valdidate_bank_for_wire_transfer()

	def validate_payment_request_amount(self):
		existing_payment_request_amount = flt(
			get_existing_payment_request_amount(
				self.reference_doctype, self.reference_name
			)
		)

		docname = None
		if frappe.flags.update_amount or not self.is_new():
			docname = self.name

		existing_payment_request_amount_drafted = flt(
			get_existing_payment_request_amount(
				self.reference_doctype,
				self.reference_name,
				submitted=False,
				update=docname,
			)
		)

		total_existing_payment_request_amount = (
			existing_payment_request_amount + existing_payment_request_amount_drafted
		)

		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)

		if (
			not hasattr(ref_doc, "order_type")
			or getattr(ref_doc, "order_type") != "Shopping Cart"
		):
			if self.reference_doctype in ["Purchase Order"]:
				ref_amount = flt(ref_doc.rounded_total) or flt(ref_doc.grand_total)
			elif self.reference_doctype in ["Purchase Invoice"]:
				if ref_doc.rounded_total:
					ref_amount = flt(ref_doc.rounded_total)
				else:
					ref_amount = flt(ref_doc.grand_total)
			else:
				ref_amount = get_amount(ref_doc, self.payment_account)

			frappe.log_error(
				"existing_payment_request_amount_drafted",
				existing_payment_request_amount_drafted,
			)
			frappe.log_error(
				"existing_payment_request_amount", existing_payment_request_amount
			)
			frappe.log_error("ref_amount", ref_amount)
			frappe.log_error("self.net_total", self.net_total)

			if total_existing_payment_request_amount + flt(self.net_total) > ref_amount:
				frappe.throw(
					frappe._(
						"Total Bank Payment Request amount cannot be greater than {0} amount"
					).format(self.reference_doctype)
				)

	def on_submit(self):
		if not self.grand_total:
			frappe.throw("Amount cannot be zero")

		debit_account = None
		if self.payment_type:
			debit_account = frappe.db.get_value(
				"Payment Type", self.payment_type, "account"
			)
		elif self.reference_doctype == "Purchase Invoice":
			debit_account = frappe.db.get_value(
				self.reference_doctype, self.reference_name, "credit_to"
			)

		if not debit_account:
			frappe.throw(
				"Debit account for Payment Type <b>{}</b> cannot be determined".format(
					self.payment_type
				)
			)
		if not self.is_adhoc:
			super().on_submit()
		else:
			if self.payment_request_type == "Outward":
				self.db_set("status", "Initiated")
				return

	def create_payment_entry(self, submit=True):
		payment_entry = super().create_payment_entry(submit=submit)
		payment_entry.source_doctype = self.payment_order_type
		if payment_entry.docstatus != 1 and self.payment_type:
			payment_entry.paid_to = (
				frappe.db.get_value("Payment Type", self.payment_type, "account") or ""
			)

		return payment_entry

	def calculate_pr_tds(self, amount):
		doc = self
		doc.supplier = self.party
		doc.company = self.company
		doc.base_tax_withholding_net_total = amount
		doc.tax_withholding_net_total = amount
		doc.taxes = []
		taxes = get_party_tax_withholding_details(doc, self.tax_withholding_category)
		if taxes:
			return taxes["tax_amount"]
		else:
			return 0

	def valdidate_bank_for_wire_transfer(self):
		if self.mode_of_payment == "Wire Transfer" and not self.bank_account:
			frappe.throw(frappe._("Bank Account is missing for Wire Transfer Payments"))

		try:
			status = frappe.db.get_value(
				"Bank Account", self.bank_account, "workflow_state"
			)

			if self.mode_of_payment == "Wire Transfer" and status != "Approved":
				frappe.throw("Cannot proceed with un-approved bank account")
		except Exception:
			return
			frappe.throw("Workflow Not Found for Bank Account")


def get_amount(ref_doc, payment_account=None):
	"""get amount based on doctype"""
	dt = ref_doc.doctype
	if dt in ["Sales Order", "Purchase Order"]:
		grand_total = flt(ref_doc.rounded_total) or flt(ref_doc.grand_total)
	elif dt in ["Sales Invoice", "Purchase Invoice"]:
		if not ref_doc.get("is_pos"):
			if ref_doc.party_account_currency == ref_doc.currency:
				if ref_doc.rounded_total:
					grand_total = flt(ref_doc.rounded_total)
				else:
					grand_total = flt(ref_doc.grand_total)
			else:
				if ref_doc.base_rounded_total:
					grand_total = (
						flt(ref_doc.base_rounded_total) / ref_doc.conversion_rate
					)
				else:
					grand_total = (
						flt(ref_doc.base_grand_total) / ref_doc.conversion_rate
					)
		elif dt == "Sales Invoice":
			for pay in ref_doc.payments:
				if pay.type == "Phone" and pay.account == payment_account:
					grand_total = pay.amount
					break
	elif dt == "POS Invoice":
		for pay in ref_doc.payments:
			if pay.type == "Phone" and pay.account == payment_account:
				grand_total = pay.amount
				break
	elif dt == "Fees":
		grand_total = ref_doc.outstanding_amount

	if grand_total > 0:
		return grand_total
	else:
		frappe.throw(frappe._("Bank Payment Entry is already created"))

@frappe.whitelist()
def make_payment_order(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc

	def set_missing_values(source, target):
		target.payment_order_type = "Payment Request"
		account = ""
		if source.payment_type:
			account = frappe.db.get_value("Payment Type", source.payment_type, "account")
		if source.reference_doctype == "Purchase Invoice":
			account = frappe.db.get_value(source.reference_doctype, source.reference_name, "credit_to")

		for dimension in get_accounting_dimensions():
			target.update({dimension: source.get(dimension, '')})

		target.append(
			"references",
			{
				"reference_doctype": source.reference_doctype,
				"reference_name": source.reference_name,
				"amount": source.grand_total,
				"party_type": source.party_type,
				"party": source.party,
				"payment_request": source_name,
				"mode_of_payment": source.mode_of_payment,
				"bank_account": source.bank_account,
				"account": account,
				"is_adhoc": source.is_adhoc,
				"cost_center": source.cost_center,
				"project": source.project,
				"tax_withholding_category": source.tax_withholding_category,
				"remarks": source.remarks,
				"payment_term": source.payment_term
			},
		)
		target.status = "Pending"

	doclist = get_mapped_doc(
		"Payment Request",
		source_name,
		{
			"Payment Request": {
				"doctype": "Payment Order",
			}
		},
		target_doc,
		set_missing_values,
	)

	return doclist

def get_existing_payment_request_amount(ref_dt, ref_dn, submitted= True, update=None, payment_term= None):
	"""
	Get the existing Bank payment request which are unpaid or partially paid for payment channel other than Phone
	and get the summation of existing paid Bank payment request for Phone payment channel.
	"""

	docstatus = 1 if submitted else 0

	where_conditions = "AND payment_term = '{0}'".format(payment_term.replace("%", "%%")) if payment_term  else "AND payment_term is null"

	existing_payment_request_amount = frappe.db.sql(
		"""
		select sum(net_total)
		from `tabPayment Request`
		where
			name != %s
			and reference_doctype = %s
			and reference_name = %s
			and docstatus = %s {0}
	""".format(where_conditions),
		(update or "", ref_dt, ref_dn, docstatus)
	)
	return flt(existing_payment_request_amount[0][0]) if existing_payment_request_amount else 0