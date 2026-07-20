app_name = "omnexa_backup"
app_title = "ERPGENEX — Backup"
app_publisher = "ErpGenEx"
app_description = "Scheduled backups with local path, FTP, Google Drive, and email (omnexa_backup)"
app_email = "dev@erpgenex.com"
app_license = "mit"

required_apps = ["omnexa_core"]

before_install = "omnexa_backup.install.enforce_supported_frappe_version"
before_migrate = "omnexa_backup.install.enforce_supported_frappe_version"

scheduler_events = {
	"cron": {
		"*/15 * * * *": [
			"omnexa_backup.backup_scheduler.on_scheduler_tick",
		],
	},
}

before_request = ["omnexa_backup.license_gate.before_request"]

doctype_js = {"Omnexa Backup Policy": "public/js/omnexa_backup_policy.js"}

# translations
# -----------

# required_apps in pyproject / hooks ensures omnexa_core for license helpers
