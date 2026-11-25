from .model import Reading
from .service import Monitor, is_high
from .sources import ReplaySource


def main() -> None:
    samples = [
        Reading("AHU-01", 23.5),
        Reading("AHU-02", 25.5),
        Reading("AHU-01", 26.0),
    ]
    monitor = Monitor(ReplaySource(samples), history_size=2)
    for _ in samples:
        reading = monitor.poll()
        status = "HIGH" if is_high(reading, limit_c=25.0) else "OK"
        print(f"{reading.sensor_id} {reading.celsius:.1f} C {status}")

    recent = [reading.celsius for reading in monitor.recent()]
    print(f"recent: {recent}")


if __name__ == "__main__":
    main()
