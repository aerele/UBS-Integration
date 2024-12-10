// Copyright (c) 2023, Aerele Technologies Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Payment Type", {
  onload: function (frm) {
    frm.set_query("account", function (doc) {
      return {
        filters: {
          is_group: 0,
          disabled: 0,
          account_type: "Payable",
          company: doc.company,
        },
      };
    });
  },
});
