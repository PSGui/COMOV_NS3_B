#!/usr/bin/env python3
"""Fast, synthetic P3 pilot harness regression tests (no ns-3 required)."""
import csv
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_p3_pilots import CASES, prefix_for, valid_existing, load_summary  # noqa: E402


class P3PilotsTests(unittest.TestCase):
    def test_exactly_eight_distinct_controlled_experiments(self):
        self.assertEqual(len(CASES), 8)
        self.assertEqual(len(set(CASES)), 8)
        self.assertIn(("reference", "immediate", 2, 4000000), CASES)
        self.assertIn(("reference", "fifo", 2, 4000000), CASES)
        self.assertIn(("fading", "immediate", 2, 4000000), CASES)
        self.assertIn(("fading", "fifo", 2, 4000000), CASES)
        self.assertIn(("contention", "immediate", 2, 4000000), CASES)
        self.assertIn(("contention", "fifo", 2, 4000000), CASES)
        self.assertIn(("reference", "fifo", 3, 4000000), CASES)
        self.assertIn(("reference", "fifo", 2, 2000000), CASES)
        self.assertEqual(len({
            str(prefix_for(a,b,15,0,1,c,d)) for a,b,c,d in CASES
        }), 8)

    def test_existing_reuse_checks_all_stressor_parameters(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "p3_fading_v15_stop0_run1_fifo_pace2_buf4000000"
            header = [
                "scenario", "policy", "speed_mps", "stop_s", "ap_x_m",
                "run", "seed", "generated", "pacing_ms", "buffer_limit_bytes",
                "background_rate_bps"
            ]
            row = ["fading", "fifo", 15, 0, 0, 1, 1, 12000, 2, 4000000, 0]
            with Path(str(path)+"_summary.csv").open("w", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(header)
                writer.writerow(row)
            self.assertFalse(valid_existing(path,"fading","fifo",15,0,1,2,4000000))
            Path(str(path)+"_analysis.json").write_text("{}", encoding="utf-8")
            Path(str(path)+"_association_raw.csv").write_text(
                "t_s,callback,already_open,sta_is_associated,bus_x_m,distance_ap_m,ap_mac\n",
                encoding="utf-8")
            for radio in ("ap", "bus"):
                Path(str(path)+f"_pcap_{radio}-0-0.pcap").write_bytes(b"synthetic-pcap")
            self.assertTrue(valid_existing(path,"fading","fifo",15,0,1,2,4000000))
            self.assertFalse(valid_existing(path,"contention","fifo",15,0,1,2,4000000))
            self.assertFalse(valid_existing(path,"fading","fifo",15,0,1,3,4000000))
            self.assertFalse(valid_existing(path,"fading","fifo",15,0,1,2,2000000))

    def test_isolated_src_has_true_fading_and_competition(self):
        p3 = (ROOT / "src/b10-p3-stress.cc").read_text(encoding="utf-8")
        p2 = (ROOT / "src/b10-p2-buffer-compare.cc").read_text(encoding="utf-8")
        self.assertIn("NakagamiPropagationLossModel", p3)
        self.assertIn("g.loss->SetNext(fading)", p3)
        self.assertIn("g.monitorLoss->CalcRxPower", p3)
        self.assertIn("backgroundTraffic.SetConstantRate", p3)
        self.assertIn("backgroundRxPackets", p3)
        self.assertIn("ErpOfdmRate6Mbps", p3)
        self.assertIn("associationRawCsv", p3)
        self.assertIn('phy.EnablePcap(prefix + "_pcap_ap"', p3)
        self.assertIn('phy.EnablePcap(prefix + "_pcap_bus"', p3)
        p3_reviewer = (ROOT / "scripts/review_p3.py").read_text(
            encoding="utf-8")
        self.assertIn("ignored_deassoc_callbacks", p3_reviewer)
        p3_pack = (ROOT / "scripts/pack_p3_results.py").read_text(
            encoding="utf-8")
        self.assertIn("association_raw.csv", p3_pack)
        self.assertIn(".pcap", p3_pack)
        self.assertNotIn("NakagamiPropagationLossModel", p2)
        self.assertNotIn("backgroundRxPackets", p2)


if __name__ == "__main__":
    unittest.main()
