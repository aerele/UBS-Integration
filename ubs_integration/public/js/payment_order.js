frappe.ui.form.on("Payment Order", {
  onload(frm) {
    if (frm.is_new()) {
      cur_frm.clear_table("references");
    }

    frm.set_query("company_bank_account", function (doc) {
      return {
        filters: {
          company: doc.company,
          is_company_account: 1,
        },
      };
    });
  },
  refresh(frm) {
    frm.set_df_property("summary", "cannot_delete_rows", true);
    frm.set_df_property("summary", "cannot_add_rows", true);
    frm.remove_custom_button("Payment Request", __("Get Payments from"));
    frm.remove_custom_button("Create Journal Entries");
    frm.trigger("remove_button");

    frm.set_query("party_type", "references", function () {
      return {
        filters: {
          name: ["in", ["Supplier", "Employee"]],
        },
      };
    });
    frm.set_query("mode_of_transfer", "summary", function () {
      return {
        filters: {
          disabled: 0,
        },
      };
    });

    frm.add_custom_button(
      __("Payment Request"),
      function () {
        frm.trigger("fetch_from_payment_request");
      },
      __("Get Payments from")
    );
    if (frm.doc.docstatus == 1) {
      frm.add_custom_button(__("Export PAIN"), function () {
        frm.trigger("export_pain");
      });
    }
  },
  export_pain(frm) {
    frm.call({
      doc: frm.doc,
      method: "export_pain_file",
      freeze: true,
      freeze_message: __("Exporting Data"),
      callback: function (r) {
        setTimeout(() => {
          frm.reload_doc();
        }, 1000);
      },
    });
  },
  remove_button: function (frm) {
    // remove custom button of order type that is not imported

    let label = ["Payment Request", "Payment Entry"];

    if (
      (frm.doc.references.length > 0 && frm.doc.payment_order_type) ||
      frm.doc.docstatus != 0
    ) {
      label = label.reduce((x) => {
        x != frm.doc.payment_order_type;
        return x;
      });
      frm.remove_custom_button(label, "Get Payments from");
    }
  },
  fetch_from_payment_request(frm) {
    console.log(2);

    frm.trigger("remove_row_if_empty");
    erpnext.utils.map_current_doc({
      method: "ubs_integration.overrides.payment_request.make_payment_order",
      source_doctype: "Payment Request",
      target: frm,
      setters: {
        party_type: "Supplier",
        party: frm.doc.supplier || "",
      },
      get_query_filters: {
        bank: frm.doc.bank,
        docstatus: 1,
        status: ["=", "Initiated"],
      },
    });
  },
  get_summary: function (frm) {
    if (frm.doc.docstatus > 0) {
      frappe.msgprint("Not allowed to change post submission");
      return;
    }
    if (!frm.doc.company_bank_account) {
      frappe.msgprint("Please Select Company Bank Account");
      return;
    }
    frm.call({
      doc: frm.doc,
      method: "get_party_summary",
      freeze: true,
      freeze_message: __("Summarizing Table"),
      callback: function (r) {
        let is_party_wise = 0;
        if (r.message && !r.exc) {
          let summary_data = r.message;
          frm.clear_table("summary");
          var doc_total = 0;
          for (var i = 0; i < summary_data.length; i++) {
            if (summary_data[i].is_party_wise && !is_party_wise) {
              is_party_wise = 1;
            }
            doc_total += summary_data[i].amount;
            let row = frm.add_child("summary");
            row.party_type = summary_data[i].party_type;
            row.party = summary_data[i].party;
            row.amount = summary_data[i].amount;
            row.bank_account = summary_data[i].bank_account;
            row.account = summary_data[i].account;
            row.mode_of_transfer = summary_data[i].mode_of_transfer;
            row.cost_center = summary_data[i].cost_center;
            row.project = summary_data[i].project;
            row.tax_withholding_category =
              summary_data[i].tax_withholding_category;
            row.reference_doctype = summary_data[i].reference_doctype;
            row.reference_name = summary_data[i].reference_name;
            row.payment_entry = summary_data[i].payment_entry;
            row.journal_entry = summary_data[i].journal_entry;
            row.remarks = summary_data[i].remarks;
            row.journal_entry_account = summary_data[i].journal_entry_account;
          }
          if (is_party_wise) {
            frm.set_value("is_party_wise", 1);
          } else {
            frm.set_value("is_party_wise", 0);
          }
          frm.refresh_field("summary");
          frm.doc.total = doc_total;
          frm.refresh_fields();
        }
      },
    });
  },
});

frappe.ui.form.on("Payment Order Summary", {
  setup: function (frm) {
    frm.set_query("party_type", function () {
      return {
        query: "erpnext.setup.doctype.party_type.party_type.get_party_type",
      };
    });
  },
});
frappe.ui.form.on("Payment Order Reference", {
  setup: function (frm) {
    frm.set_query("party_type", function () {
      return {
        query: "erpnext.setup.doctype.party_type.party_type.get_party_type",
      };
    });
  },
});
