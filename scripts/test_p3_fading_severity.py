#!/usr/bin/env python3
"""Regression tests for controlled Nakagami fading severity experiment."""
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_p3_fading_severity import prefix_for  # noqa: E402


class SeverityTests(unittest.TestCase):
    def test_isolated_unique_names_for_eight_cases(self):
        names = {
            str(prefix_for(m, policy, 1, use_static))
            for m in (3, 5)
            for use_static in (False, True)
            for policy in ("immediate", "fifo")
        }
        self.assertEqual(len(names), 8)
        self.assertTrue(all("_m3" in p or "_m5" in p for p in names))
        self.assertTrue(any("staticarp_macdiag_m5" in p for p in names))
        self.assertFalse(any("_m1" in p for p in names))

    def test_the_original_p2_source_is_not_changed(self):
        p3 = (ROOT / "src/b10-p3-stress.cc").read_text(encoding="utf-8")
        p2 = (ROOT / "src/b10-p2-buffer-compare.cc").read_text(encoding="utf-8")
        script = (ROOT / "scripts/run_p3.sh").read_text(encoding="utf-8")
        self.assertIn('double fadingM{1.0}', p3)
        self.assertIn('fading->SetAttribute("m0", DoubleValue(fadingM))', p3)
        self.assertIn('fading->SetAttribute("m1", DoubleValue(fadingM))', p3)
        self.assertIn('fading->SetAttribute("m2", DoubleValue(fadingM))', p3)
        self.assertIn('NS_ABORT_MSG_IF(scenario != "fading" && fadingM != 1.0', p3)
        self.assertIn('fading_m', p3)
        self.assertNotIn("fadingM", p2)
        self.assertIn('FADING_M="${11:-1}"', script)
        self.assertIn('PREFIX="${PREFIX}_m${FADING_M}"', script)
        self.assertIn('--fadingM=$FADING_M', script)


if __name__ == "__main__":
    unittest.main()
