"""Synthetic single water pump; validates arithmetic, not equipment selection."""
import argparse
import json
import math
import unittest

G = 9.80665
RHO = 998.0


def checked(x, label, *, zero=False):
    if not math.isfinite(x) or x < 0 or (not zero and x == 0):
        raise ValueError(f"invalid {label}")
    return x


def area(diameter_m):
    return math.pi * checked(diameter_m, "inside diameter") ** 2 / 4


def velocity(flow_m3h, diameter_m):
    return checked(flow_m3h, "flow", zero=True) / 3600 / area(diameter_m)


def pressure_head(delta_pa, rho=RHO):
    return checked(delta_pa, "pressure drop", zero=True) / (checked(rho, "density") * G)


def system_head(q, static_m=0):
    # Representative closed loop: 150 m of pipe, ID 150 mm, Darcy f=.022,
    # sum K=14. Coil, filter and other equipment cost 130 kPa at 120 m3/h.
    v = velocity(q, 0.15)
    pipe = (0.022 * 150 / 0.15 + 14) * v * v / (2 * G)
    equipment = pressure_head(130_000) * (q / 120) ** 2
    return checked(static_m, "static head", zero=True) + pipe + equipment


def pump_head(q, speed=1):
    # Synthetic reference curve, not valid beyond its declared plot domain.
    checked(q, "flow", zero=True)
    if not 0.7 <= speed <= 1 or q > 180 * speed:
        raise ValueError("outside synthetic pump curve range")
    return speed ** 2 * (32 - 12 * (q / speed / 120) ** 2)


def operating_point(speed=1, static_m=0):
    lo, hi = 0.0, 180 * speed
    def residual(q):
        return pump_head(q, speed) - system_head(q, static_m)
    if not residual(lo) > 0 > residual(hi):
        raise ValueError("no positive intersection in curve range")
    for _ in range(65):
        mid = (lo + hi) / 2
        if residual(mid) > 0:
            lo = mid
        else:
            hi = mid
    q = (lo + hi) / 2
    return q, system_head(q, static_m)


def powers(q, head, pump_eta, motor_eta, drive_eta):
    if any(not 0 < eta <= 1 for eta in (pump_eta, motor_eta, drive_eta)):
        raise ValueError("efficiency must be >0 and <=1")
    hydraulic = RHO * G * (checked(q, "flow", zero=True) / 3600) * checked(head, "head", zero=True) / 1000
    shaft = hydraulic / pump_eta
    return hydraulic, shaft, shaft / motor_eta / drive_eta


def npsha(suction_abs_pa, vapor_abs_pa, suction_velocity_m_s):
    # Suction static pressure at the pump reference plane; same elevation datum.
    head = pressure_head(suction_abs_pa) - pressure_head(vapor_abs_pa)
    return head + checked(suction_velocity_m_s, "suction velocity", zero=True) ** 2 / (2 * G)


def model():
    q, h = operating_point()
    q8, h8 = operating_point(.8)
    p = powers(q, h, .76, .92, .97)
    v = velocity(q, .15)
    return {
        "point": {"flow_m3h": q, "head_m": h, "velocity_m_s": v,
                  "delta_kpa": h * RHO * G / 1000,
                  "hydraulic_kw": p[0], "shaft_kw": p[1], "electrical_kw": p[2],
                  "npsha_m": npsha(135_000, 1_230, v)},
        "speed_80": {"flow_m3h": q8, "head_m": h8},
        "open_8m_point": dict(zip(("flow_m3h","head_m"), operating_point(1,8))),
        "curve": [{"q": q, "pump_100": pump_head(q), "system": system_head(q),
                   "system_with_8m_static": system_head(q,8),
                   "pump_80": pump_head(q,.8) if q <= 144 else None}
                  for q in range(0,181,4)],
    }


class LabTests(unittest.TestCase):
    def test_continuity_and_pressure(self):
        self.assertAlmostEqual(velocity(120, .15) * area(.15) * 3600, 120)
        self.assertAlmostEqual(pressure_head(RHO * G * 10), 10)

    def test_point_residual(self):
        q, h = operating_point()
        self.assertAlmostEqual(h, pump_head(q))
        self.assertEqual(system_head(0), 0)
        self.assertEqual(system_head(0, 8), 8)
        self.assertLess(operating_point(static_m=8)[0], q)

    def test_affinity_closed_not_open(self):
        self.assertAlmostEqual(operating_point(.8)[0] / operating_point()[0], .8)
        self.assertNotAlmostEqual(
            operating_point(.8, 8)[0] / operating_point(1, 8)[0], .8)

    def test_power_and_suction(self):
        hydraulic, shaft, electrical = powers(120, 20, .76, .92, .97)
        self.assertTrue(hydraulic < shaft < electrical)
        self.assertLess(npsha(135_000, 10_000, 2), npsha(135_000, 1230, 2))

    def test_reject_invalid(self):
        for call in (lambda: velocity(-1,.15), lambda: velocity(5,0),
                     lambda: pressure_head(float("nan")), lambda: powers(2, 2, 0, .9, .9),
                     lambda: pump_head(150,.8), lambda: operating_point(1,40)):
            with self.assertRaises(ValueError):
                call()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        unittest.main(argv=["lab"], verbosity=2)
    else:
        print(json.dumps(model(), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
