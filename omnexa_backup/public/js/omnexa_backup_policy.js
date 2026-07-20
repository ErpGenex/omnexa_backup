// Copyright (c) 2026, Omnexa and contributors
// License: MIT. See license.txt

frappe.ui.form.on("Omnexa Backup Policy", {
	refresh(frm) {
		if (frm.doc.__islocal || !frappe.user.has_role("System Manager")) {
			return;
		}
		frm.add_custom_button(__("Run backup now"), () => {
			frappe.call({
				method: "omnexa_backup.backup_api.trigger_backup_now",
				freeze: true,
				freeze_message: __("Queueing backup..."),
				callback(r) {
					const m = r.message && r.message.message;
					frappe.msgprint(m || __("Queued"));
				},
			});
		});
	},
});
