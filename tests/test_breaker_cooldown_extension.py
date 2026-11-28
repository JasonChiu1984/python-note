from pathlib import Path
import runpy

import pytest


Breaker = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                             "extensions/python_integration_resilience_tutorial/example.py"))["CircuitBreaker"]


@pytest.mark.parametrize(("seconds", "at_41"), [(30, "失敗"), (60, "略過")])
def test_same_timeline_under_both_cooldowns(seconds, at_41):
    t = [0]
    breaker = Breaker(cooldown=seconds, clock=lambda: t[0])
    def fail():
        raise ConnectionError("offline")
    result = {}
    for instant in (0, 5, 10, 15, 25, 41, 75):
        t[0] = instant
        result[instant] = breaker.call((lambda: "OK") if instant == 75 else fail)
    assert result[41].startswith(at_41)
    assert result[75] == "成功：OK"
    assert breaker.state == "closed"


def test_failed_probe_starts_cooldown_when_it_finishes():
    t = [0]
    breaker = Breaker(threshold=1, cooldown=30, clock=lambda: t[0])
    def fail():
        raise ConnectionError("offline")
    breaker.call(fail)
    t[0] = 41
    def slow_fail():
        t[0] = 51
        fail()
    assert breaker.call(slow_fail).startswith("失敗")
    assert breaker.opened_at == 51
    t[0] = 80
    assert breaker.call(lambda: "OK").startswith("略過")
    t[0] = 81
    assert breaker.call(lambda: "OK") == "成功：OK"
