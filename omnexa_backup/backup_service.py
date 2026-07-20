# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import os
from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import escape_html, get_datetime, get_time, getdate, now_datetime, split_emails, today
from frappe.utils.backups import new_backup

_WEEKDAY_INDEX = {
	"Monday": 0,
	"Tuesday": 1,
	"Wednesday": 2,
	"Thursday": 3,
	"Friday": 4,
	"Saturday": 5,
	"Sunday": 6,
}


def _license_allows_backup() -> bool:
	try:
		from omnexa_core.omnexa_core.omnexa_license import verify_app_license
	except Exception:
		return True

	if frappe.conf.get("omnexa_license_enforce") not in (1, True, "1", "true", "True"):
		return True
	r = verify_app_license("omnexa_backup")
	return r.status in ("licensed", "licensed_free", "licensed_dev_override", "trial")


def _today_at_time(time_value) -> datetime:
	if not time_value:
		t = datetime.strptime("02:00:00", "%H:%M:%S").time()
	else:
		t = get_time(str(time_value))
	return datetime.combine(getdate(today()), t)


def _is_daily_due(last_backup_on, backup_time) -> bool:
	now = now_datetime()
	slot = _today_at_time(backup_time)
	if now < slot:
		return False
	if not last_backup_on:
		return True
	last = get_datetime(last_backup_on)
	return last < slot


def _is_weekly_due(last_backup_on, backup_time, weekday: str) -> bool:
	if _WEEKDAY_INDEX.get(weekday or "", -1) != now_datetime().weekday():
		return False
	return _is_daily_due(last_backup_on, backup_time)


def _is_hourly_due(last_backup_on) -> bool:
	if not last_backup_on:
		return True
	last = get_datetime(last_backup_on)
	return (now_datetime() - last) >= timedelta(minutes=55)


def _is_every_n_hours_due(last_backup_on, n: int) -> bool:
	if not last_backup_on:
		return True
	n = max(1, min(int(n or 1), 168))
	last = get_datetime(last_backup_on)
	return (now_datetime() - last) >= timedelta(hours=n, minutes=-5)


def is_backup_due(policy: frappe._dict) -> bool:
	if not policy.enabled:
		return False
	if not policy.local_folder:
		return False

	freq = policy.frequency or "Daily"
	last = policy.last_backup_on

	if freq == "Daily":
		return _is_daily_due(last, policy.backup_time)
	if freq == "Weekly":
		return _is_weekly_due(last, policy.backup_time, policy.weekday)
	if freq == "Hourly":
		return _is_hourly_due(last)
	if freq == "Every N Hours":
		return _is_every_n_hours_due(last, policy.every_n_hours)

	return False


def maybe_enqueue_backup() -> None:
	"""Called from scheduler tick; enqueues long job if policy is due."""
	if not _license_allows_backup():
		return

	if not frappe.db.exists("DocType", "Omnexa Backup Policy"):
		return

	policy = frappe.db.get_singles_dict("Omnexa Backup Policy", cast=True)
	if not policy or not policy.enabled:
		return

	if not is_backup_due(policy):
		return

	frappe.enqueue(
		"omnexa_backup.backup_service.run_backup_job",
		queue="long",
		timeout=3600,
		job_name=f"omnexa_backup:{frappe.local.site}",
		enqueue_after_commit=True,
	)


def run_backup_job(trigger: str = "schedule") -> None:
	"""Take backup, optional FTP/GDrive, email, retention. Run in background worker."""
	if not _license_allows_backup():
		frappe.log_error("omnexa_backup: skipped (license)", "Omnexa Backup")
		return

	policy = frappe.get_single("Omnexa Backup Policy")
	if not policy.enabled:
		return

	local_folder = (policy.local_folder or "").strip()
	if not local_folder or not os.path.isabs(local_folder):
		frappe.throw(_("Invalid backup folder."))

	os.makedirs(local_folder, exist_ok=True)

	ignore_files = not (policy.include_public_files or policy.include_private_files)

	try:
		odb = new_backup(
			older_than=24,
			ignore_files=ignore_files,
			backup_path=local_folder,
			force=True,
			verbose=False,
		)
	except Exception as e:
		_set_policy_status("Failed", str(e)[:2000])
		_send_notification(False, str(e), policy)
		frappe.db.commit()
		raise

	paths = []
	for p in (odb.backup_path_db, odb.backup_path_conf, odb.backup_path_files, odb.backup_path_private_files):
		if p and os.path.isfile(p):
			paths.append(p)

	_cleanup_old_backups(local_folder, int(policy.retention_days or 14), odb.site_slug)

	ftp_error = None
	if policy.enable_ftp:
		try:
			_upload_paths_ftp(paths, policy)
		except Exception as e:
			ftp_error = str(e)
			frappe.log_error(frappe.get_traceback(), "Omnexa Backup FTP")

	gdrive_error = None
	if policy.upload_to_google_drive:
		try:
			_upload_paths_google_drive(paths)
		except Exception as e:
			gdrive_error = str(e)
			frappe.log_error(frappe.get_traceback(), "Omnexa Backup Google Drive")

	ok = not (ftp_error or gdrive_error)
	msg_parts = [f"Site {frappe.local.site}", f"Files: {len(paths)}"]
	if ftp_error:
		msg_parts.append(f"FTP error: {ftp_error}")
	if gdrive_error:
		msg_parts.append(f"Google Drive error: {gdrive_error}")

	status = "Success" if ok else "Partial (see errors)"
	full_err = "\n".join([x for x in (ftp_error, gdrive_error) if x]) or None
	_set_policy_status(status, full_err)

	if ok:
		policy.db_set("last_backup_on", now_datetime(), update_modified=False)
	else:
		policy.db_set("last_backup_on", now_datetime(), update_modified=False)

	frappe.db.commit()

	if ok:
		_send_notification(True, "\n".join(msg_parts), policy)
	else:
		_send_notification(False, "\n".join(msg_parts), policy)


def _set_policy_status(status: str, err: str | None) -> None:
	frappe.db.set_single_value(
		"Omnexa Backup Policy",
		{
			"last_backup_status": status[:140] if status else None,
			"last_error": (err or "")[:2000] if err else None,
		},
	)


def _send_notification(success: bool, body: str, policy) -> None:
	emails = split_emails(policy.notification_emails or "")
	if not emails:
		return
	if success and not policy.notify_on_success:
		return
	if not success and not policy.notify_on_failure:
		return

	subject = _("Omnexa backup succeeded") if success else _("Omnexa backup failed")
	try:
		frappe.sendmail(recipients=emails, subject=str(subject), message=f"<pre>{escape_html(body)}</pre>")
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa Backup email")


def _cleanup_old_backups(folder: str, retention_days: int, site_slug: str) -> None:
	if retention_days <= 0:
		return
	cutoff = now_datetime() - timedelta(days=retention_days)
	prefix = site_slug
	try:
		for name in os.listdir(folder):
			if prefix not in name:
				continue
			path = os.path.join(folder, name)
			if not os.path.isfile(path):
				continue
			mtime = datetime.fromtimestamp(os.path.getmtime(path))
			if mtime < cutoff:
				os.remove(path)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa Backup retention")


def _upload_paths_ftp(paths: list[str], policy) -> None:
	import ftplib

	host = policy.ftp_host.strip()
	user = policy.ftp_username.strip()
	password = policy.get_password("ftp_password") or ""
	port = int(policy.ftp_port or 21)
	remote_base = (policy.ftp_remote_directory or "/").strip() or "/"
	use_tls = bool(policy.ftp_use_tls)

	if use_tls:
		ftp = ftplib.FTP_TLS()
	else:
		ftp = ftplib.FTP()
	ftp.connect(host, port, timeout=120)
	ftp.login(user, password)
	if use_tls:
		ftp.prot_p()

	try:
		try:
			ftp.cwd("/")
		except Exception:
			pass
		if remote_base and remote_base != "/":
			_ftp_makedirs(ftp, remote_base)
			ftp.cwd(remote_base)

		for local in paths:
			fn = os.path.basename(local)
			with open(local, "rb") as f:
				ftp.storbinary(f"STOR {fn}", f, 1024 * 1024)
	finally:
		try:
			ftp.quit()
		except Exception:
			pass


def _ftp_makedirs(ftp: "ftplib.FTP", remote_path: str) -> None:
	parts = [p for p in remote_path.replace("\\", "/").split("/") if p]
	for p in parts:
		try:
			ftp.cwd(p)
		except Exception:
			ftp.mkd(p)
			ftp.cwd(p)


def _upload_paths_google_drive(paths: list[str]) -> None:
	from apiclient.http import MediaFileUpload
	from googleapiclient.errors import HttpError

	enabled = frappe.db.get_single_value("Google Drive", "enable")
	if not enabled:
		frappe.throw(_("Enable and authorize Google Drive under Integrations → Google Drive first."))

	from frappe.integrations.doctype.google_drive.google_drive import (
		check_for_folder_in_google_drive,
		get_google_drive_object,
	)

	google_drive, account = get_google_drive_object()
	check_for_folder_in_google_drive()
	account.load_from_db()
	folder_id = account.backup_folder_id
	if not folder_id:
		frappe.throw(_("Google Drive backup folder is not ready."))

	for local in paths:
		if not local or not os.path.isfile(local):
			continue
		file_metadata = {"name": os.path.basename(local), "parents": [folder_id]}
		mime = "application/gzip" if local.endswith(".gz") else ("application/x-tar" if local.endswith(".tar") else "application/octet-stream")
		media = MediaFileUpload(local, mimetype=mime, resumable=True)
		try:
			google_drive.files().create(body=file_metadata, media_body=media, fields="id").execute()
		except HttpError as e:
			frappe.throw(_("Google Drive upload failed: {0}").format(e))
