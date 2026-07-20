# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import os

import frappe
from frappe import _
from frappe.model.document import Document


class OmnexaBackupPolicy(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		backup_time: DF.Time | None
		enabled: DF.Check
		every_n_hours: DF.Int
		ftp_host: DF.Data | None
		ftp_password: DF.Password | None
		ftp_port: DF.Int
		ftp_remote_directory: DF.Data | None
		ftp_username: DF.Data | None
		ftp_use_tls: DF.Check
		frequency: DF.Literal["Daily", "Hourly", "Every N Hours", "Weekly"]
		include_database: DF.Check
		include_private_files: DF.Check
		include_public_files: DF.Check
		last_backup_on: DF.Datetime | None
		last_backup_status: DF.Data | None
		last_error: DF.Text | None
		local_folder: DF.Data
		notification_emails: DF.SmallText | None
		notify_on_failure: DF.Check
		notify_on_success: DF.Check
		retention_days: DF.Int
		upload_to_google_drive: DF.Check
		weekday: DF.Literal[
			"Monday",
			"Tuesday",
			"Wednesday",
			"Thursday",
			"Friday",
			"Saturday",
			"Sunday",
		] | None

	# end: auto-generated types

	def validate(self):
		# Database dump is always produced by Frappe backup; flags control whether public/private files are included.
		if self.local_folder:
			p = self.local_folder.strip()
			if not os.path.isabs(p):
				frappe.throw(_("Backup folder must be an absolute path."))
			self.local_folder = os.path.abspath(p)

		if self.frequency == "Weekly" and not self.weekday:
			frappe.throw(_("Select a weekday for weekly backups."))
		if self.frequency in {"Daily", "Weekly"} and not self.backup_time:
			frappe.throw(_("Backup time is mandatory for Daily/Weekly schedule."))

		if self.frequency == "Every N Hours":
			n = int(self.every_n_hours or 0)
			if n < 1 or n > 168:
				frappe.throw(_("Every N hours must be between 1 and 168."))
		if int(self.retention_days or 0) < 1:
			frappe.throw(_("Retention days must be at least 1."), title=_("Retention"))

		if self.enable_ftp:
			if not self.ftp_host or not self.ftp_username:
				frappe.throw(_("FTP host and username are required when FTP upload is enabled."))
			if not self.get_password("ftp_password"):
				frappe.throw(_("FTP password is required when FTP upload is enabled."))
		if (self.notify_on_success or self.notify_on_failure) and not (self.notification_emails or "").strip():
			frappe.throw(_("Notification emails are required when email notifications are enabled."))
		if not self.change_ticket:
			frappe.throw(_("Change Ticket is mandatory for backup policy governance."))
		if not self.policy_reference:
			frappe.throw(_("Policy Reference is mandatory for backup policy governance."))
