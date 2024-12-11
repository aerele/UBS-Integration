import random
import re
import string
import xml.etree.ElementTree as ET

import frappe
from erpnext.accounts.doctype.payment_order.payment_order import PaymentOrder
from frappe import _, bold
from frappe.utils import cstr, getdate


class BankPaymentOrder(PaymentOrder):
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
                    )

                return (
                    ref.party_type,
                    ref.party,
                    ref.bank_account,
                    ref.account,
                    ref.cost_center,
                    ref.project,
                    ref.tax_withholding_category,
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
