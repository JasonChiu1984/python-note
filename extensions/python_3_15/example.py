"""確認目前直譯器是否為 free-threaded 建置，並示範「每執行緒部分和再合併」與「共享計數器加鎖」兩種寫法。

輸出只印正確性與建置資訊，不印執行時間（時間每次不同，且受核心數影響）。
在 free-threaded 建置（python3.15t）上，未加鎖的共享計數器更容易出現遺失更新。
"""
import sys
import sysconfig
import threading
from concurrent.futures import ThreadPoolExecutor

N_THREADS, PER_THREAD = 4, 50_000


def partial_sum(start):
    return sum(range(start, start + PER_THREAD))


def locked_counter():
    total = 0
    lock = threading.Lock()

    def work():
        nonlocal total
        for _ in range(PER_THREAD):
            with lock:
                total += 1

    threads = [threading.Thread(target=work) for _ in range(N_THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return total


if __name__ == "__main__":
    print(f"Python {sys.version_info.major}.{sys.version_info.minor}")
    built_ft = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))
    gil = sys._is_gil_enabled() if hasattr(sys, "_is_gil_enabled") else True
    print(f"free-threaded 建置：{built_ft}；目前 GIL 啟用：{gil}")
    with ThreadPoolExecutor(N_THREADS) as pool:
        parts = list(pool.map(partial_sum, range(0, N_THREADS * PER_THREAD, PER_THREAD)))
    expected = sum(range(N_THREADS * PER_THREAD))
    print(f"部分和合併：{sum(parts)}，與單執行緒結果相同：{sum(parts) == expected}")
    print(f"加鎖共享計數器：{locked_counter()}（應為 {N_THREADS * PER_THREAD}）")
    print("建議：CPU 密集工作優先讓每個執行緒處理獨立資料再合併，共享可變狀態要加鎖或改用 queue。")
