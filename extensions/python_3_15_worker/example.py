"""asyncio 工作管線：有界佇列背壓、TaskGroup 結構化併發、停機時記錄未完成項目（需 Python 3.11+）。

consumer 拋出自訂的 Shutdown 例外時，TaskGroup 會取消其他子任務（producer），再把例外包成
ExceptionGroup 往外丟，用 except* 接住。Python 3.15 起也可以從外部呼叫 TaskGroup.cancel()。
"""
import asyncio
import sys

QUEUE_SIZE = 3


class Shutdown(Exception):
    pass


async def producer(q, readings, log):
    for r in readings:
        await q.put(r)                    # 佇列滿時在這裡等待：背壓
        log.append(f"put {r}")
    await q.put(None)


async def consumer(q, out, log, stop_after):
    while True:
        r = await q.get()
        if r is None:
            return
        await asyncio.sleep(0)            # 模擬 I/O 讓出控制權
        out.append(r * 2)
        log.append(f"done {r}")
        if len(out) == stop_after:
            raise Shutdown(f"收到停機要求，已處理 {len(out)} 筆")


async def run(stop_after=None):
    q: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_SIZE)
    out, log, reason = [], [], None
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(producer(q, list(range(1, 9)), log))
            tg.create_task(consumer(q, out, log, stop_after or 999))
    except* Shutdown as eg:
        reason = str(eg.exceptions[0])
    left = []
    while not q.empty():
        item = q.get_nowait()
        if item is not None:
            left.append(item)
    return out, log, left, reason


if __name__ == "__main__":
    print(f"Python {sys.version_info.major}.{sys.version_info.minor}；TaskGroup.cancel 可用：{hasattr(asyncio.TaskGroup, 'cancel')}")
    out, log, left, _ = asyncio.run(run())
    print("完整執行：", out)
    print("前 6 個事件：", log[:6])
    out, log, left, reason = asyncio.run(run(stop_after=3))
    print(reason, "→ 已完成", out, "；佇列中未處理", left)
    print("producer 已被 TaskGroup 取消，最後送出的是", [e for e in log if e.startswith("put")][-1])
