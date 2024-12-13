frappe.ui.form.on("Payment Order", {
  onload(frm) {
	if (frm.is_new()) {
	  frm.clear_table("references");
	  frm.clear_table("summary");
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
	frm.remove_custom_button("Payment Request", "Get Payments from");

	frm.trigger("enable_button");

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
	frm.trigger("remove_button");
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
  enable_button: function (frm) {
	frm.add_custom_button(
	  __("Payment Request"),
	  function () {
		frm.trigger("fetch_from_payment_request");
	  },
	  __("Get Payments from")
	);
	const status_details = frm.doc.summary?.reduce((acc, item) => {
	  acc[item.payment_status.toLowerCase()] =
		(acc[item.payment_status.toLowerCase()] || 0) + 1;
	  return acc;
	}, {});

	if (frm.doc.docstatus == 1 && status_details.pending > 0) {
	  frm.add_custom_button(__("Update Status"), function () {
		frm.trigger("show_status_dialog");
	  });
	}
	if (!frm.is_new()) {
	  frm.add_custom_button(__("Export PAIN"), function () {
		frm.trigger("export_pain");
	  });
	}
  },

  show_status_dialog: function (frm) {
	frm.data = [];
	const dialog = new frappe.ui.Dialog({
	  title: __("Payment Summary"),
	  size: "extra-large",
	  fields: [
		{
		  fieldname: "summary",
		  fieldtype: "Table",
		  label: __("Summary"),
		  data: frm.data,
		  in_place_edit: true,
		  cannot_add_rows: true,
		  cannot_delete_rows: true,
		  get_data: () => {
			return frm.data;
		  },
		  fields: [
			{
			  label: __("Row Name"),
			  fieldname: "row_name",
			  fieldtype: "data",
			  read_only: 1,
			},
			{
				label: __("payment_order"),
				fieldname: "payment_order",
				fieldtype: "data",
				hidden: 1
			  },
			{
			  label: __("Party Type"),
			  fieldname: "party_type",
			  fieldtype: "Link",
			  options: "DocType",
			  in_list_view: 1,
			  columns: 1,
			  read_only: 1,
			  get_query: () => {
				return {
				  filters: {
					company: frm.doc.company,
					name: ["in", ["Supplier", "Employee"]],
				  },
				};
			  },
			},
			{
			  label: __("Party"),
			  fieldname: "party",
			  fieldtype: "Dynamic Link",
			  options: "party_type",
			  columns: 2,
			  in_list_view: 1,
			  read_only: 1,
			},
			{
			  label: __("Amount"),
			  fieldname: "amount",
			  fieldtype: "Currency",
			  in_list_view: 1,
			  columns: 1,
			  read_only: 1,
			},
			{
			  label: __("Status"),
			  fieldname: "status",
			  fieldtype: "Select",
			  options: "\nProcessed\nFailed",
			  columns: 1,
			  in_list_view: 1,
			},
			{
			  label: __("Payment Date"),
			  fieldname: "payment_date",
			  fieldtype: "Date",
			  columns: 1,
			  in_list_view: 1,
			},
			{
			  label: __("Reference Number"),
			  fieldname: "reference_number",
			  fieldtype: "Data",
			  columns: 2,
			  in_list_view: 1,
			},
			{
				label: __("Payment Entry"),
				fieldname: "payment_entry",
				fieldtype: "Data",
				hidden: 1,
			  },
		  ],
		},
		{
		  fieldtype: "HTML",
		  options: `<p>To update the payment status, please provide the following information:</p>
										<ul>
											<li><strong>Payment Date:</strong> Enter the date when the payment was made.</li>  
											<li><strong>Reference Number:</strong> Input the transaction or reference number associated with this payment for tracking purposes.</li>  
										</ul>
										<p>Ensure that both details are accurate to facilitate a smooth update of your payment status.</p>`,
		},
	  ],
	  primary_action: () => {
		frm.call({
		  method:
			"ubs_integration.overrides.payment_order.update_payment_status",
		  args: {
			data: dialog.get_values()["summary"],
		  },
		  freeze: true,
		  freeze_message: __("Updating Status..."),
		  callback: function (r) {
			dialog.hide();
			frm.reload_doc();
		  },
		});
	  },
	  primary_action_label: __("Update"),
	});

	var row = 0;
	frm.doc.summary.forEach((d) => {
	  if (["Pending", "Initiated"].includes(d.payment_status)) {
		row += 1;
		dialog.fields_dict.summary.df.data.push({
		  payment_order: frm.doc.name,
		  row: row,
		  row_name: d.name,
		  party_type: d.party_type,
		  party: d.party,
		  amount: d.amount,
		  payment_entry: d.payment_entry
		});
	  }
	});

	frm.data = [];
	dialog.show();
	dialog.fields_dict.summary.grid.refresh();
	dialog.$wrapper.find(".grid-row-check").prop("disabled", 1);
  },
  remove_button: function (frm) {
	frm.remove_custom_button("Create Journal Entries");

	if (
	  (frm.doc.references.length > 0 && frm.doc.payment_order_type) ||
	  frm.doc.docstatus != 0
	) {
	  if (
		frm.doc.payment_order_type == "Payment Request" ||
		frm.doc.docstatus != 0
	  ) {
		frm.remove_custom_button("Payment Entry", "Get Payments from");
	  }
	  if (
		frm.doc.payment_order_type == "Payment Entry" ||
		frm.doc.docstatus != 0
	  ) {
		frm.remove_custom_button("Payment Request", "Get Payments from");
	  }
	}
  },
  fetch_from_payment_request(frm) {
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
