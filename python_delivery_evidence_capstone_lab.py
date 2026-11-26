"""離線合成範例：以受信任的預期摘要核對交付檔組合。Python 3.11+。"""
import argparse
import hashlib
import json
import unittest

REQUIRED = ("README.md", "report.json", "runbook.md")


def manifest(artifacts: dict[str, bytes]) -> bytes:
    """只有教材允許的三個名稱；不解壓、不讀本機路徑。"""
    if set(artifacts) != set(REQUIRED):
        raise ValueError("artifact set mismatch")
    rows = [{"name": name, "size": len(artifacts[name]),
             "sha256": hashlib.sha256(artifacts[name]).hexdigest()}
            for name in sorted(artifacts)]
    return json.dumps({"schema": 1, "artifacts": rows}, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def assess(artifacts: dict[str, bytes], expected_digest: str,
           tests_passed: bool, rollback_rehearsed: bool) -> str:
    """教學關卡傳回第一個決策；不執行部署。"""
    if set(artifacts) != set(REQUIRED):
        return "blocked: artifact set"
    if hashlib.sha256(manifest(artifacts)).hexdigest() != expected_digest:
        return "blocked: digest"
    if not tests_passed:
        return "blocked: tests"
    if not rollback_rehearsed:
        return "blocked: rollback"
    return "ready for authorized promotion"


BUNDLE = {"README.md": b"how to replay", "report.json": b'{"items": 3}',
          "runbook.md": b"rollback checklist"}


class Tests(unittest.TestCase):
    def setUp(self):
        self.expected = hashlib.sha256(manifest(BUNDLE)).hexdigest()

    def test_reproducible_order(self):
        self.assertEqual(manifest(BUNDLE), manifest(dict(reversed(list(BUNDLE.items())))))

    def test_gates(self):
        wrong = {**BUNDLE, "report.json": b'{"items": 4}'}
        missing = {k: v for k, v in BUNDLE.items() if k != "runbook.md"}
        self.assertEqual(assess(BUNDLE, self.expected, True, True),
                         "ready for authorized promotion")
        self.assertEqual(assess(wrong, self.expected, True, True), "blocked: digest")
        self.assertEqual(assess(missing, self.expected, True, True), "blocked: artifact set")
        self.assertEqual(assess(BUNDLE, self.expected, False, True), "blocked: tests")
        self.assertEqual(assess(BUNDLE, self.expected, True, False), "blocked: rollback")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--changed-fixture", action="store_true")
    args = parser.parse_args()
    if args.test:
        return 0 if unittest.TextTestRunner().run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful() else 1
    # 模擬從已核准版本取得預期摘要；正式部署不能由候選輸入自行重算。
    expected = hashlib.sha256(manifest(BUNDLE)).hexdigest()
    candidate = {**BUNDLE, "report.json": b'{"items": 4}'} if args.changed_fixture else BUNDLE
    status = assess(candidate, expected, True, True)
    print(status)
    return 1 if status.startswith("blocked:") else 0


if __name__ == "__main__":
    raise SystemExit(main())
