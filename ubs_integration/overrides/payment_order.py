import frappe
from erpnext.accounts.doctype.payment_order.payment_order import PaymentOrder

class BankPaymentOrder(PaymentOrder):
	@frappe.whitelist()
	def get_party_summary(self):
		summarise_payment_based_on = frappe.get_single("Bank Integration Settings").summarise_payment_based_on
		def _get_unique_key(ref=None, summarise_field=False):
			if summarise_payment_based_on == "Party":
				if summarise_field:
					return  ("party_type", "party", "bank_account", "account", "cost_center", "project",
					"tax_withholding_category")

				return (ref.party_type, ref.party, ref.bank_account, ref.account, ref.cost_center, ref.project,
				ref.tax_withholding_category)

			elif summarise_payment_based_on == "Voucher":
				if summarise_field:
					return ('party_type', 'party', 'reference_doctype', 'reference_name', 'bank_account',
					'account', 'cost_center', 'project', 'tax_withholding_category')

				return (ref.party_type, ref.party, ref.reference_doctype, ref.reference_name, ref.bank_account,
				ref.account, ref.cost_center, ref.project, ref.tax_withholding_category)

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
		print(remarks_list)

		result = []
		for key, val in summary.items():
			summary_line_item = {k: v for k, v in zip(_get_unique_key(summarise_field=True), key) }
			summary_line_item["amount"] = val
			summary_line_item["remarks"] = remarks_list[key]
			if summarise_payment_based_on == "Party":
				summary_line_item["is_party_wise"] = 1
			else:
				summary_line_item["is_party_wise"] = 0

			result.append(summary_line_item)

		for row in result:
			party_bank = frappe.db.get_value("Bank Account", row["bank_account"], "bank")
			company_bank = frappe.db.get_value("Bank Account", self.company_bank_account, "bank")
			row["mode_of_transfer"] = None
			if party_bank == company_bank:
				mode_of_transfer = frappe.db.get_value("Mode of Transfer", {"is_bank_specific": 1, "bank": party_bank})
				if mode_of_transfer:
					row["mode_of_transfer"] = mode_of_transfer
			else:
				mot = frappe.db.get_value("Mode of Transfer", {
					"minimum_limit": ["<=", row["amount"]],
					"maximum_limit": [">", row["amount"]],
					"is_bank_specific": 0
					},
					order_by = "priority asc")
				if mot:
					row["mode_of_transfer"] = mot

		return result