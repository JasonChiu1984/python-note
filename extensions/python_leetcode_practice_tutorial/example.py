"""把刷題技巧用在現場資料：滑動視窗找最長超溫區間、雙指標合併兩條時間序列、單調堆疊找下一次升溫（標準函式庫）。"""
from collections import deque

TEMPS = [24.1, 25.3, 28.4, 28.9, 29.2, 27.5, 28.6, 29.0, 29.4, 28.8, 26.0, 28.3]


def longest_above(values, limit):
    """一次掃描：O(n) 找最長連續超溫段（類似「最長連續 1」）。"""
    best, start, cur = (0, -1), None, 0
    for i, v in enumerate(values):
        if v > limit:
            start = i if start is None else start
            if i - start + 1 > best[0]:
                best = (i - start + 1, start)
        else:
            start = None
    return best


def max_in_windows(values, k):
    """單調佇列：O(n) 求每個長度 k 視窗的最大值（LeetCode 239）。"""
    dq, out = deque(), []
    for i, v in enumerate(values):
        while dq and values[dq[-1]] <= v:
            dq.pop()
        dq.append(i)
        if dq[0] <= i - k:
            dq.popleft()
        if i >= k - 1:
            out.append(values[dq[0]])
    return out


def merge_sorted(a, b):
    """雙指標合併兩條已排序的 (時間, 來源) 序列，O(n + m)。"""
    i = j = 0
    out = []
    while i < len(a) and j < len(b):
        if a[i][0] <= b[j][0]:
            out.append(a[i]); i += 1
        else:
            out.append(b[j]); j += 1
    return out + a[i:] + b[j:]


def next_warmer(values):
    """單調堆疊：每個時間點要等幾步才會更熱（LeetCode 739）。"""
    ans, stack = [0] * len(values), []
    for i, v in enumerate(values):
        while stack and values[stack[-1]] < v:
            j = stack.pop()
            ans[j] = i - j
        stack.append(i)
    return ans


if __name__ == "__main__":
    length, start = longest_above(TEMPS, 28.0)
    print(f"最長連續超過 28 °C：{length} 筆，從索引 {start} 開始 → {TEMPS[start:start + length]}")
    print("每 3 筆視窗最大值：", max_in_windows(TEMPS, 3))
    a = [(1, "AHU1"), (4, "AHU1"), (9, "AHU1")]
    b = [(2, "CH1"), (4, "CH1"), (7, "CH1")]
    print("合併時間序列：", merge_sorted(a, b))
    print("幾步後更熱：", next_warmer(TEMPS))
