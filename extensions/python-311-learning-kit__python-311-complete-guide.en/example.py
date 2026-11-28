"""Python 3.11: poll concurrently with TaskGroup, handle errors by type with except*, read config with tomllib (needs 3.11+)."""
import asyncio
import tomllib

CONFIG = tomllib.loads("""
[poll]
timeout_s = 0.05
[[device]]
name = "M01"
delay = 0.01
[[device]]
name = "M02"
delay = 0.2
[[device]]
name = "M03"
delay = -1
""")


async def read(dev):
    if dev["delay"] < 0:
        raise ConnectionRefusedError(f"{dev['name']} refused the connection")
    async with asyncio.timeout(CONFIG["poll"]["timeout_s"]):
        await asyncio.sleep(dev["delay"])
    return dev["name"], 22.5


async def main():
    results = {}
    try:
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(read(d)) for d in CONFIG["device"]]
    except* TimeoutError as eg:
        print(f"{len(eg.exceptions)} device(s) timed out")
    except* ConnectionError as eg:
        print("Connection errors:", [str(e) for e in eg.exceptions])
    for t in tasks:
        if t.done() and not t.cancelled() and t.exception() is None:
            results.update([t.result()])
    print("Succeeded:", results)


if __name__ == "__main__":
    print("Config:", [d["name"] for d in CONFIG["device"]], "timeout", CONFIG["poll"]["timeout_s"], "s")
    asyncio.run(main())
