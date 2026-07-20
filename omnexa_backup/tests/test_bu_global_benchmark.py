# Copyright (c) 2026, Omnexa
from frappe.tests.utils import FrappeTestCase
from omnexa_backup.bu_gap_register import GLOBAL_LEADER_TARGET, get_gap_status
from omnexa_backup.bu_global_benchmark import get_global_bu_score

class TestBuGlobalBenchmark(FrappeTestCase):
	def test_global_score(self):
		s = get_global_bu_score()
		self.assertGreaterEqual(s["weighted_score"], GLOBAL_LEADER_TARGET)
		self.assertTrue(s.get("global_leader_gate"))

	def test_gaps_closed(self):
		self.assertTrue(get_gap_status()["global_leader_gate"])
