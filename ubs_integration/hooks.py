app_name = "ubs_integration"
app_title = "UBS Integration"
app_publisher = "Aerele Technologies Private Limited"
app_description = "Union Bank of Switzerland Integration with ERPNext"
app_email = "support@aerele.in"
app_license = "gpl-3.0"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "ubs_integration",
# 		"logo": "/assets/ubs_integration/logo.png",
# 		"title": "UBS Integration",
# 		"route": "/ubs_integration",
# 		"has_permission": "ubs_integration.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/ubs_integration/css/ubs_integration.css"
# app_include_js = "/assets/ubs_integration/js/ubs_integration.js"

# include js, css files in header of web template
# web_include_css = "/assets/ubs_integration/css/ubs_integration.css"
# web_include_js = "/assets/ubs_integration/js/ubs_integration.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "ubs_integration/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
doctype_js = {
    "Payment Request": "public/js/payment_request.js",
    "Payment Order": "public/js/payment_order.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "ubs_integration/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "ubs_integration.utils.jinja_methods",
# 	"filters": "ubs_integration.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "ubs_integration.install.before_install"
after_install = "ubs_integration.setup.install.after_install"
before_uninstall = "ubs_integration.setup.install.before_uninstall"


# Uninstallation
# ------------

# before_uninstall = "ubs_integration.uninstall.before_uninstall"
# after_uninstall = "ubs_integration.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "ubs_integration.utils.before_app_install"
# after_app_install = "ubs_integration.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "ubs_integration.utils.before_app_uninstall"
# after_app_uninstall = "ubs_integration.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "ubs_integration.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
    "Payment Request": "ubs_integration.overrides.payment_request.BankPaymentRequest",
    "Payment Order": "ubs_integration.overrides.payment_order.BankPaymentOrder",
}

accounting_dimension_doctypes = ["Payment Order Reference", "Payment Order Summary"]

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"ubs_integration.tasks.all"
# 	],
# 	"daily": [
# 		"ubs_integration.tasks.daily"
# 	],
# 	"hourly": [
# 		"ubs_integration.tasks.hourly"
# 	],
# 	"weekly": [
# 		"ubs_integration.tasks.weekly"
# 	],
# 	"monthly": [
# 		"ubs_integration.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "ubs_integration.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "ubs_integration.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "ubs_integration.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["ubs_integration.utils.before_request"]
# after_request = ["ubs_integration.utils.after_request"]

# Job Events
# ----------
# before_job = ["ubs_integration.utils.before_job"]
# after_job = ["ubs_integration.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"ubs_integration.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }
