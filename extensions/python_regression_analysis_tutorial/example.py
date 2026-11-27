"""時序切分、與「沿用昨天」基準比較、殘差漂移偵測（標準函式庫 statistics）。"""
from statistics import fmean, linear_regression

# 每日外氣平均溫度（°C）與冰水系統用電（MWh），前 20 天訓練、後 10 天測試；第 26 天起冰機結垢效率變差
TEMP = [24.1, 25.3, 26.0, 27.2, 26.8, 28.1, 29.0, 28.4, 27.5, 26.9,
        27.8, 29.3, 30.1, 30.8, 29.9, 28.7, 29.5, 30.6, 31.2, 30.4,
        29.8, 30.9, 31.5, 32.0, 31.1, 30.7, 31.8, 32.4, 31.9, 32.6]
KWH = [18.2, 19.5, 20.1, 21.6, 21.0, 22.8, 23.9, 23.1, 22.0, 21.3,
       22.4, 24.3, 25.2, 26.1, 25.0, 23.6, 24.6, 25.8, 26.6, 25.7,
       25.0, 26.4, 27.1, 27.8, 26.7, 27.3, 28.9, 29.8, 29.4, 30.4]
SPLIT = 20


def mae(a, b):
    return fmean(abs(x - y) for x, y in zip(a, b))


if __name__ == "__main__":
    slope, intercept = linear_regression(TEMP[:SPLIT], KWH[:SPLIT])
    print(f"訓練期模型：MWh = {intercept:.2f} + {slope:.3f} × 溫度")
    pred = [intercept + slope * t for t in TEMP[SPLIT:]]
    naive = KWH[SPLIT - 1:-1]                                # 沿用前一天的值
    actual = KWH[SPLIT:]
    print(f"測試期 MAE：迴歸 {mae(pred, actual):.2f}、沿用昨天 {mae(naive, actual):.2f} MWh")
    train_res = [y - (intercept + slope * x) for x, y in zip(TEMP[:SPLIT], KWH[:SPLIT])]
    limit = 3 * (fmean(r * r for r in train_res) ** 0.5)
    print(f"殘差告警門檻 ±{limit:.2f} MWh（訓練期殘差 RMS 的 3 倍）")
    for day, (p, a) in enumerate(zip(pred, actual), start=SPLIT + 1):
        r = a - p
        flag = "  ← 超出門檻，檢查設備" if abs(r) > limit else ""
        print(f"  第 {day} 天 預測 {p:5.2f} 實際 {a:5.2f} 殘差 {r:+.2f}{flag}")
