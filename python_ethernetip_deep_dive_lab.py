"""解碼合成的 Assembly 資料；非網路封包、不連線、不寫入設備。"""
from dataclasses import dataclass
import math
from struct import Struct
import unittest

# 教學自訂映射：小端序 uint16 旗標、int16 0.01°C、uint32 序號。
LAYOUT = Struct("<HhI")
FAN_RUNNING = 1 << 0
SENSOR_VALID = 1 << 1
SYNTHETIC = bytes.fromhex("0300 2909 2a000000")


@dataclass(frozen=True)
class Feedback:
    fan_running: bool
    temp_c: float | None
    producer_seq: int


def decode(payload: bytes) -> Feedback:
    if len(payload) != LAYOUT.size:
        raise ValueError("Assembly 資料長度不符教學映射")
    flags, centi_c, seq = LAYOUT.unpack(payload)
    return Feedback(bool(flags & FAN_RUNNING),
                    centi_c / 100 if flags & SENSOR_VALID else None,
                    seq)


def quality(feedback: Feedback, now: float, received_at: float,
            local_budget_s: float) -> str:
    """使用同一 monotonic 時鐘，只量測最近接收年齡。"""
    if not all(map(math.isfinite, (now, received_at, local_budget_s))):
        raise ValueError("時間須為有限值")
    if local_budget_s <= 0 or received_at > now:
        raise ValueError("須使用同一時鐘且接收時間不得晚於當前時間")
    if now - received_at >= local_budget_s:
        return "STALE"
    return "GOOD" if feedback.temp_c is not None else "BAD_SENSOR"


class Tests(unittest.TestCase):
    def test_known_payload(self):
        self.assertEqual(decode(SYNTHETIC), Feedback(True, 23.45, 42))

    def test_lengths_and_quality_bit(self):
        for invalid in (SYNTHETIC[:-1], SYNTHETIC + b"\0"):
            with self.assertRaises(ValueError):
                decode(invalid)
        bad = decode(LAYOUT.pack(FAN_RUNNING, -123, 7))
        self.assertEqual(bad, Feedback(True, None, 7))
        self.assertEqual(quality(bad, .01, 0, .06), "BAD_SENSOR")

    def test_signed_value_and_local_stale(self):
        result = decode(LAYOUT.pack(SENSOR_VALID, -250, 8))
        self.assertEqual(result, Feedback(False, -2.5, 8))
        self.assertEqual(quality(result, .01, 0, .06), "GOOD")
        self.assertEqual(quality(result, .06, 0, .06), "STALE")
        with self.assertRaises(ValueError):
            quality(result, 0, .01, .06)


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        unittest.main(argv=["lab"])
    else:
        sample = decode(SYNTHETIC)
        print(sample)
        print("接收後 10 ms:", quality(sample, .010, 0, .060))
        print("接收後 80 ms:", quality(sample, .080, 0, .060))
