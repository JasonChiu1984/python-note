"""Python 3.15 官方 Classes 教程的可攜式補充範例。"""


def scope_demo():
    def make_probe():
        tag = "zone"

        class Probe:
            tag = "class"

            def labels(self):
                return tag, self.tag

        return Probe()

    probe = make_probe()
    print(probe.labels())
    probe.tag = "instance"
    print(probe.labels())


def binding_demo():
    class Probe:
        unit = "C"

        def __init__(self, offset):
            self.__offset = offset

        def calibrate(self, value):
            return value + self.__offset

    probe = Probe(0.5)
    read = probe.calibrate
    print(read(24.0), Probe.calibrate(probe, 24.0))
    print(read.__self__ is probe)
    print(read.__func__ is Probe.calibrate)
    print("_Probe__offset" in vars(probe))
    probe.unit = "degC"
    print(Probe.unit, probe.unit)


def inheritance_demo():
    class Probe:
        def describe(self):
            return ["probe"]

    class TaggedProbe(Probe):
        def describe(self):
            return ["tagged", *super().describe()]

    class CalibratedProbe(Probe):
        def describe(self):
            return ["calibrated", *super().describe()]

    class SmartProbe(TaggedProbe, CalibratedProbe):
        pass

    probe = SmartProbe()
    print([cls.__name__ for cls in SmartProbe.__mro__])
    print(probe.describe())
    print(isinstance(probe, Probe), issubclass(SmartProbe, Probe))


def iterator_demo():
    class ReadingCursor:
        def __init__(self, values):
            self._values = iter(values)

        def __iter__(self):
            return self

        def __next__(self):
            return next(self._values)

    class Trend:
        def __init__(self, values):
            self._values = tuple(values)

        def __iter__(self):
            return ReadingCursor(self._values)

    trend = Trend([24.0, 25.5])
    cursor = iter(trend)
    print(next(cursor), list(cursor), list(cursor))
    print(list(trend), list(trend))


def generator_demo():
    def high_values(values, limit):
        for value in values:
            if value >= limit:
                yield value

    highs = high_values([24.0, 25.5, 26.0], 25.0)
    print(next(highs), list(highs), list(highs))

    batches = [[23.5, 25.5], [], [26.0]]
    merged = (value for batch in batches for value in batch)
    print(list(merged))


def main():
    for demo in (scope_demo, binding_demo, inheritance_demo,
                 iterator_demo, generator_demo):
        print(f"\n{demo.__name__}")
        demo()


if __name__ == "__main__":
    main()
