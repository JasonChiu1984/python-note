"""初學者綜合練習：串列、字典、迴圈、函式與 f-string，整理一天的溫度紀錄（標準函式庫）。"""

readings = [
    ("08:00", 23.1), ("09:00", 24.6), ("10:00", 26.2), ("11:00", 27.8),
    ("12:00", 28.5), ("13:00", 29.1), ("14:00", 28.7), ("15:00", 27.4),
]


def classify(temp):
    if temp >= 28:
        return "偏熱"
    if temp >= 25:
        return "注意"
    return "舒適"


def summary(rows):
    temps = [t for _, t in rows]                     # 串列推導式
    counts = {}
    for _, t in rows:
        level = classify(t)
        counts[level] = counts.get(level, 0) + 1     # 字典計數
    return {"最高": max(temps), "最低": min(temps), "平均": round(sum(temps) / len(temps), 1), "分類": counts}


if __name__ == "__main__":
    for time, temp in readings:
        print(f"{time}  {temp:>4.1f} °C  {classify(temp)}")
    s = summary(readings)
    print("摘要：", s)
    hot = [time for time, temp in readings if temp >= 28]
    print(f"偏熱時段共 {len(hot)} 小時：{', '.join(hot)}")
