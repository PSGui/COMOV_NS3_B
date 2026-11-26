#!/usr/bin/env python3
"""P3 MAC-path diagnostic regression checks. No ns-3 runtime required."""
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_p3_mac_path_diagnostic import prefix, valid_diag  # noqa: E402


class MacPathDiagnosticTests(unittest.TestCase):
    def test_isolated_artifact_names(self):
        for policy in ("immediate", "fifo"):
            original = str(prefix(policy, 1))
            traced = str(prefix(policy, 1, diag=True))
            self.assertNotEqual(original, traced)
            self.assertTrue(traced.endswith("_staticarp_macdiag"))
            self.assertFalse(original.endswith("_macdiag"))

    def test_mac_traces_are_diagnostic_only(self):
        p3 = (ROOT / "src/b10-p3-stress.cc").read_text(encoding="utf-8")
        p2 = (ROOT / "src/b10-p2-buffer-compare.cc").read_text(encoding="utf-8")
        runner = (ROOT / "scripts/run_p3.sh").read_text(encoding="utf-8")
        self.assertIn("bool macDiagnostics{false}", p3)
        self.assertIn("macDiagnostics && !(scenario == \"fading\" && staticArp)", p3)
        self.assertIn("apMac->IsAssociated", p3)
        self.assertIn('TraceConnectWithoutContext(\n                            "MacRx"', p3)
        self.assertIn('TraceConnectWithoutContext(\n                            "MacRxDrop"', p3)
        self.assertIn('TraceConnectWithoutContext(\n                            "MacPromiscRx"', p3)
        self.assertIn("OnApIpv4Rx", p3)
        self.assertIn("mac_path_summary.csv", p3)
        self.assertIn("MAC_DIAG", runner)
        self.assertIn("_macdiag", runner)
        self.assertNotIn("macDiagnostics", p2)

    def test_cannot_reuse_incomplete_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            fake = Path(folder) / "p3_fading_v15_stop0_run1_fifo_pace2_buf4000000_staticarp_macdiag"
            self.assertFalse(valid_diag(fake, 1, "fifo"))


if __name__ == "__main__":
    unittest.main()
