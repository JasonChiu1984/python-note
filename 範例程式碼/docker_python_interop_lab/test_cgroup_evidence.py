import copy
import tempfile
import unittest
from pathlib import Path

from cgroup_evidence import compare, locate, parse_counters


class EvidenceTests(unittest.TestCase):
    def locate_fixture(self, group, root, members, nested=""):
        with tempfile.TemporaryDirectory(prefix="cgroup test ") as tmp:
            proc = Path(tmp, "proc")
            proc.mkdir()
            mount = Path(tmp, "leaf")
            (mount / nested).mkdir(parents=True)
            (mount / nested / "cgroup.procs").write_text(members)
            (proc / "cgroup").write_text(f"0::{group}\n")
            name = str(mount).replace(" ", r"\040")
            (proc / "mountinfo").write_text(f"1 0 0:0 {root} {name} ro - cgroup2 cgroup rw\n")
            found = locate(proc, 42)
            if found:
                self.assertEqual(found[0], mount / nested)
            return bool(found)

    def test_container_root_is_membership_checked(self):
        self.assertTrue(self.locate_fixture("/", "/docker/x", "7\n42\n"))

    def test_host_path_with_non_root_mount(self):
        self.assertTrue(self.locate_fixture("/slice/a", "/slice", "42\n", "a"))

    def test_other_cgroup_rejected(self):
        self.assertFalse(self.locate_fixture("/", "/", "142\n"))

    def test_parent_escape_rejected(self):
        self.assertFalse(self.locate_fixture("/../leaf", "/", "42\n"))

    def test_counter_missing_is_not_zero(self):
        self.assertEqual(parse_counters("oom_kill 0\n", ["oom", "oom_kill"]),
                         {"oom": None, "oom_kill": 0})

    @staticmethod
    def fixture():
        a = {"schema": 1, "status": "ok", "boot_id": "boot", "identity": [1, 2],
             "sample_unix_ns": 1, "scalars": {"cpu.max": "max 100000"},
             "counters": {"cpu.stat": {"nr_throttled": 4}}}
        b = copy.deepcopy(a)
        b["sample_unix_ns"] += 1
        b["counters"]["cpu.stat"]["nr_throttled"] += 3
        return a, b

    def test_diff(self):
        a, b = self.fixture()
        b["scalars"]["cpu.max"] = "50000 100000"
        data = compare(a, b)
        self.assertEqual(data["delta"]["cpu.stat"]["nr_throttled"], 3)
        self.assertIsNone(data["delta"]["memory.events.local"]["oom_kill"])
        self.assertEqual(data["configuration_changed"], ["cpu.max"])

    def test_restart_and_reset_not_delta(self):
        a, b = self.fixture()
        for key, value in (("identity", [1, 3]), ("boot_id", "new"), ("sample_unix_ns", 1)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                compare(a, dict(b, **{key: value}))
        b["counters"]["cpu.stat"]["nr_throttled"] = 1
        with self.assertRaisesRegex(ValueError, "counter reset"):
            compare(a, b)

    def test_unknown_is_not_a_delta(self):
        a, b = self.fixture()
        b["status"] = "unavailable"
        with self.assertRaises(ValueError):
            compare(a, b)
