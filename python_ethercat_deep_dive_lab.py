"""Evaluate fixed synthetic EtherCAT monitoring records; no I/O or fieldbus access."""

from dataclasses import dataclass
import argparse
import json
import unittest


@dataclass(frozen=True)
class Record:
    cycle: int
    state: str                    # Reported state of the monitored I/O domain
    wkc: int | None               # None = this frame did not return by deadline
    sample_ms: int | None         # Aligned sample timestamp; None if not supplied
    observed_ms: int
    dc_ok: bool                   # True/False per upstream monitor's own policy


def classify(records: tuple[Record, ...], *, expected: int,
             freshness_ms: int, require_dc: bool) -> list[dict]:
    """The result drives a dashboard, not equipment. All thresholds are fictional."""
    if expected <= 0 or freshness_ms < 0:
        raise ValueError("expected WKC must be positive; freshness cannot be negative")
    result = []
    failures = good = 0
    alarm = False
    previous_cycle = -1
    previous_observed = -1
    for r in records:
        if r.cycle <= previous_cycle or r.observed_ms < previous_observed:
            raise ValueError("records must be sorted by increasing monitor cycle and time")
        previous_cycle, previous_observed = r.cycle, r.observed_ms
        age = None if r.sample_ms is None else r.observed_ms - r.sample_ms
        if r.wkc is None:
            reason = "timeout"
        elif r.state != "OP":
            reason = "not_op"
        elif r.wkc != expected:
            reason = "wkc_mismatch"
        elif age is None:
            reason = "sample_time_unknown"
        elif not 0 <= age <= freshness_ms:
            reason = "stale_or_time_alignment"
        elif require_dc and not r.dc_ok:
            reason = "dc_out_of_policy"
        else:
            reason = "ok"

        if reason == "ok":
            good += 1
            failures = 0
            if good >= 2:
                alarm = False
        else:
            failures += 1
            good = 0
            if failures >= 2:
                alarm = True
        result.append({"cycle": r.cycle, "data_valid": reason == "ok",
                       "reason": reason, "age_ms": age, "alarm": alarm})
    return result


RECORDS = (
    Record(71, "OP", 3, 100, 101, True),
    Record(72, "OP", 3, 100, 109, True),   # WKC matches, but upstream sample is old
    Record(73, "OP", None, None, 110, True),
    Record(74, "OP", 3, 110, 111, True),
    Record(75, "OP", 3, 111, 112, True),
    Record(76, "SAFEOP", 3, 112, 113, True),
    Record(77, "OP", 2, 113, 114, True),
    Record(78, "OP", 3, 114, 115, False),
)


class MonitorTest(unittest.TestCase):
    def test_working_counter_does_not_prove_freshness(self):
        rows = classify(RECORDS, expected=3, freshness_ms=4, require_dc=True)
        self.assertEqual([x["reason"] for x in rows],
                         ["ok", "stale_or_time_alignment", "timeout", "ok", "ok",
                          "not_op", "wkc_mismatch", "dc_out_of_policy"])
        self.assertEqual([x["alarm"] for x in rows],
                         [False, False, True, True, False, False, True, True])
        self.assertFalse(rows[1]["data_valid"])

    def test_unknown_and_future_sample_time(self):
        data = (Record(1, "OP", 3, None, 9, True), Record(2, "OP", 3, 11, 10, True))
        self.assertEqual([x["reason"] for x in
                          classify(data, expected=3, freshness_ms=4, require_dc=False)],
                         ["sample_time_unknown", "stale_or_time_alignment"])

    def test_order_matters(self):
        with self.assertRaises(ValueError):
            classify((RECORDS[1], RECORDS[0]), expected=3, freshness_ms=4, require_dc=True)

    def test_dc_policy_can_be_not_applicable(self):
        self.assertTrue(classify((RECORDS[-1],), expected=3,
                                 freshness_ms=4, require_dc=False)[0]["data_valid"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true")
    if parser.parse_args().test:
        unittest.main(argv=["lab"])
    else:
        print(json.dumps(classify(RECORDS, expected=3, freshness_ms=4, require_dc=True),
                         ensure_ascii=False, indent=2))
