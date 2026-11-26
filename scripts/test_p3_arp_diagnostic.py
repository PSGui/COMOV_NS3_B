#!/usr/bin/env python3
"""CI regression tests for P3 fading ARP diagnostic (no ns-3 required)."""
import struct
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_p3_arp_diagnostic import pcap_counts, prefix_for  # noqa: E402


def make_pcap(path, frames):
    with path.open("wb") as stream:
        stream.write(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 105))
        for frame in frames:
            stream.write(struct.pack("<IIII", 61, 100000, len(frame), len(frame)))
            stream.write(frame)


def data_frame(ether_type, arp_opcode=None):
    hdr = bytearray(24)
    hdr[0] = 0x08
    llc = b"\xaa\xaa\x03\x00\x00\x00" + ether_type.to_bytes(2, "big")
    payload = bytearray(32)
    if arp_opcode is not None:
        payload[6:8] = arp_opcode.to_bytes(2, "big")
    return bytes(hdr + llc + payload)


class TestArpDiagnostic(unittest.TestCase):
    def test_pcap_parser_detects_arp_blockage(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "wifi.pcap"
            make_pcap(path, [
                data_frame(0x806, 1),
                data_frame(0x806, 1),
                data_frame(0x806, 2),
                data_frame(0x800),
            ])
            stats = pcap_counts(path)
            self.assertEqual(stats["frames"], 4)
            self.assertEqual(stats["arp_request"], 2)
            self.assertEqual(stats["arp_reply"], 1)
            self.assertEqual(stats["ipv4_data"], 1)

    def test_static_arp_prefix_distinct(self):
        ordinary = str(prefix_for("fifo", 1, False))
        changed = str(prefix_for("fifo", 1, True))
        self.assertNotEqual(ordinary, changed)
        self.assertTrue(changed.endswith("_staticarp"))

    def test_static_arp_is_opt_in(self):
        src = (ROOT / "src/b10-p3-stress.cc").read_text(encoding="utf-8")
        runner = (ROOT / "scripts/run_p3.sh").read_text(encoding="utf-8")
        self.assertIn('bool staticArp{false}', src)
        self.assertIn('NeighborCacheHelper neighbors;', src)
        self.assertIn('neighbors.PopulateNeighborCache();', src)
        self.assertIn('staticArp && scenario != "fading"', src)
        self.assertIn('if [[ "$STATIC_ARP" == "1" ]]', runner)
        self.assertIn('_staticarp', runner)
        self.assertNotIn('NeighborCacheHelper', (
            ROOT / "src/b10-p2-buffer-compare.cc").read_text(encoding="utf-8"))

    def test_rejects_non_80211_pcap(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "bad.pcap"
            with path.open("wb") as stream:
                stream.write(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4,
                                         0, 0, 65535, 1))
            with self.assertRaisesRegex(ValueError, "DLT"):
                pcap_counts(path)


if __name__ == "__main__":
    unittest.main()
