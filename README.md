# Omnexa Backup

Scheduled site backups (database + optional public/private files) to a configurable server folder, optional FTP upload, optional Google Drive upload (via Frappe **Google Drive** integration), and email notifications.

Requires **omnexa_core** (Omnexa license verification). Add `omnexa_backup` to `omnexa_licenses` like other paid Omnexa apps when enforcement is enabled.

## Install

```bash
bench get-app /path/to/omnexa_backup
bench --site <site> install-app omnexa_backup
bench migrate
```

Configure **Omnexa Backup Policy** (Desk). Ensure the scheduler service is running on the bench.
