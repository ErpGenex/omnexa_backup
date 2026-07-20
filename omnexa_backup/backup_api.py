# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _


@frappe.whitelist()
def trigger_backup_now():
	"""Queue a full backup run (same path as scheduled job). System Manager only."""
	frappe.only_for("System Manager")

	frappe.enqueue(
		"omnexa_backup.backup_service.run_backup_job",
		queue="long",
		timeout=3600,
		job_name=f"omnexa_backup_manual:{frappe.local.site}",
		trigger="manual",
	)

	return {"ok": True, "message": _("Backup has been queued. Check Omnexa Backup Policy for status.")}
