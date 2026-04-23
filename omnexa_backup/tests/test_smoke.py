from frappe.tests.utils import FrappeTestCase

from omnexa_backup import hooks


class TestBackupSmoke(FrappeTestCase):
	def test_hooks_are_present(self):
		self.assertEqual(hooks.app_name, "omnexa_backup")
		self.assertIn("omnexa_core", hooks.required_apps)
		self.assertIn("cron", hooks.scheduler_events)

