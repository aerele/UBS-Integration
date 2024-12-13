// Copyright (c) 2024, Aerele Technologies Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Payment Request", {
  refresh(frm) {
	if (frm.doc.status == "Initiated") {
	  frm.remove_custom_button(__("Create Payment Entry"));
	}
	frm.set_query("payment_type", function () {
	  return {
		filters: {
		  company: frm.doc.company,
		},
	  };
	});
	frm.set_query("cost_center", function (doc) {
		return {
		  filters: {
			company: doc.company,
			is_group: 0,
		  },
		};
	  });
	frm.set_query("project", function (doc) {
		return {
			filters: {
			company: doc.company
			},
		};
	});
	if(frm.doc.docstatus == 1){
		cur_frm.add_custom_button('Goto Payment Order', function(){
			frappe.set_route('List', 'Payment Order')
		})
	}
  },
  validate(frm) {
	if (!frm.doc.net_total) {
	  frm.set_value("net_total", frm.doc.grand_total);
	}
  },
  company(frm) {
	frm.set_query("payment_type", function () {
	  return {
		filters: {
		  company: frm.doc.company,
		},
	  };
	});
  },
  mode_of_payment(frm) {
	var conditions = get_bank_query_conditions(frm);
	if (frm.doc.mode_of_payment == "Wire Transfer") {
	  frm.set_query("bank_account", function () {
		return {
		  filters: conditions,
		};
	  });
	}
  },
  party_type(frm) {
	var conditions = get_bank_query_conditions(frm);
	if (frm.doc.mode_of_payment == "Wire Transfer") {
	  frm.set_query("bank_account", function () {
		return {
		  filters: conditions,
		};
	  });
	}
  },
  party(frm) {
	var conditions = get_bank_query_conditions(frm);
	if (frm.doc.mode_of_payment == "Wire Transfer") {
	  frm.set_query("bank_account", function () {
		return {
		  filters: conditions,
		};
	  });
	}
  },
  net_total(frm) {
	frm.set_value("grand_total", frm.doc.net_total - frm.doc.taxes_deducted);
  },
});

var get_bank_query_conditions = function (frm) {
  var conditions = {};
  if (frm.doc.party_type) {
	conditions["party_type"] = frm.doc.party_type;
  }
  if (frm.doc.party) {
	conditions["party"] = frm.doc.party;
  }
  if (frm.doc.mode_of_payment == "Wire Transfer") {
	frm.set_query("bank_account", function () {
	  return {
		filters: conditions,
	  };
	});
  }
  return conditions;
};
