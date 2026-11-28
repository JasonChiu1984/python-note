"""加速比的上限：Amdahl 定律與 Gustafson 定律，並列出各平台 multiprocessing 預設啟動方式（標準函式庫）。

輸出不量測本機時間，因為不同機器結果不同；量測方法請見本頁第 4 節。
"""


def amdahl(p, n):
    """固定工作量：可平行比例 p、n 個工作者的加速比上限。"""
    return 1 / ((1 - p) + p / n)


def gustafson(p, n):
    """工作量隨工作者數增加：可平行比例 p 時的擴展加速比。"""
    return (1 - p) + p * n


if __name__ == "__main__":
    workers = (1, 2, 4, 8, 16, 64)
    print("可平行比例 |" + "".join(f"{n:>7}" for n in workers))
    for p in (0.5, 0.8, 0.95, 0.99):
        print(f"Amdahl {p:4.0%} |" + "".join(f"{amdahl(p, n):7.2f}" for n in workers))
    print(f"Gustafson 95% |" + "".join(f"{gustafson(0.95, n):7.2f}" for n in workers))
    print()
    print("例：資料解析 95% 可平行，其餘 5% 是讀檔與彙總。8 核心最多約", f"{amdahl(0.95, 8):.1f}", "倍，",
          "即使 64 核心也只有", f"{amdahl(0.95, 64):.1f}", "倍（上限 20 倍）。")
    print()
    defaults = [("Linux（Python 3.14 起）", "forkserver"), ("Linux（3.13 以前）", "fork"),
                ("macOS（3.8 起）", "spawn"), ("Windows", "spawn")]
    print("multiprocessing 預設啟動方式：")
    for plat, method in defaults:
        print(f"  {plat:<22} {method}")
