# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Scheduler entrypoint (keep tiny for low import cost)."""


def on_scheduler_tick():
	from omnexa_backup.backup_service import maybe_enqueue_backup

	maybe_enqueue_backup()
