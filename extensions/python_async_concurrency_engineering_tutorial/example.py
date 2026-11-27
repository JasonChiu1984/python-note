"""asyncio 併發上限與逾時：Semaphore 限制同時連線數、wait_for 處理單台逾時、gather 收集結果不中斷（標準函式庫）。"""
import asyncio

DELAYS = {f"M{i:02d}": 0.01 for i in range(1, 9)}
DELAYS["M05"] = 1.0                       # 這台很慢
MAX_CONCURRENT, TIMEOUT = 3, 0.2


async def read_meter(name, sem, active, peak):
    async with sem:
        active[0] += 1
        peak[0] = max(peak[0], active[0])
        try:
            await asyncio.sleep(DELAYS[name])
            return name, 100 + int(name[1:])
        finally:
            active[0] -= 1


async def main():
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    active, peak = [0], [0]
    tasks = [asyncio.wait_for(read_meter(n, sem, active, peak), TIMEOUT) for n in DELAYS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    ok = {r[0]: r[1] for r in results if isinstance(r, tuple)}
    failed = [n for n, r in zip(DELAYS, results) if isinstance(r, Exception)]
    print(f"成功 {len(ok)} 台：{ok}")
    print(f"逾時 {failed}（{type(results[4]).__name__}）")
    print(f"同時連線數最高 {peak[0]}（上限 {MAX_CONCURRENT}）")


if __name__ == "__main__":
    asyncio.run(main())
