"""Python 3.11：TaskGroup 同時輪詢、except* 依例外類型分組處理、tomllib 讀設定（需 Python 3.11+）。"""
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
        raise ConnectionRefusedError(f"{dev['name']} 拒絕連線")
    async with asyncio.timeout(CONFIG["poll"]["timeout_s"]):
        await asyncio.sleep(dev["delay"])
    return dev["name"], 22.5


async def main():
    results = {}
    try:
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(read(d)) for d in CONFIG["device"]]
    except* TimeoutError as eg:
        print(f"逾時 {len(eg.exceptions)} 台")
    except* ConnectionError as eg:
        print("連線錯誤：", [str(e) for e in eg.exceptions])
    for t in tasks:
        if t.done() and not t.cancelled() and t.exception() is None:
            results.update([t.result()])
    print("成功：", results)


if __name__ == "__main__":
    print("設定：", [d["name"] for d in CONFIG["device"]], "逾時", CONFIG["poll"]["timeout_s"], "s")
    asyncio.run(main())
