"""優雅停機：收到 SIGTERM 後停止接新工作、完成手上的工作、在期限內結束（標準函式庫）。"""
import os
import signal
import threading
import time

stop = threading.Event()
log = []


def on_sigterm(signum, frame):
    log.append("收到 SIGTERM，停止接新工作")
    stop.set()


def worker(jobs):
    for j in jobs:
        if stop.is_set():
            log.append(f"略過尚未開始的 {j}（寫回佇列待下次處理）")
            continue
        log.append(f"開始 {j}")
        if j == "job-2":
            os.kill(os.getpid(), signal.SIGTERM)          # 模擬部署平台在處理中送出停止訊號
            stop.wait(1)                                   # 等主執行緒的訊號處理器執行（讓輸出順序固定）
        time.sleep(0.01)                                   # 模擬工作
        log.append(f"完成 {j}")


if __name__ == "__main__":
    if not hasattr(signal, "SIGTERM") or os.name == "nt":
        print("此範例需在 Linux／macOS 執行（Windows 的訊號模型不同）")
    else:
        signal.signal(signal.SIGTERM, on_sigterm)
        t = threading.Thread(target=worker, args=(["job-1", "job-2", "job-3", "job-4"],))
        t.start()
        t.join(timeout=5)                                  # 停機期限，應小於平台的 terminationGracePeriod
        print("\n".join(log))
        print("結束狀態：", "如期完成" if not t.is_alive() else "超過期限，強制結束")
