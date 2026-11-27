"""以冷房度日（CDD）建立能源基線、計算正規化節能量與 CUSUM（標準函式庫）。

基線期 12 個月：月用電 kWh 對 CDD 做線性迴歸。報告期把實際 CDD 代入基線模型，
得到「如果沒有改善會用多少電」，再與實際用電相減。CUSUM 累計差值，斜率轉負代表改善開始生效。
"""
from statistics import correlation, fmean, linear_regression

BASE_CDD = [12, 18, 65, 120, 210, 300, 355, 350, 270, 160, 60, 20]
BASE_KWH = [181_000, 188_100, 213_000, 245_600, 296_800, 354_000,
            393_000, 386_900, 341_700, 272_100, 212_800, 187_800]
REPORT_CDD = [15, 22, 80, 135, 230, 320, 370, 365, 280, 170, 70, 25]
REPORT_KWH = [178_000, 191_000, 225_000, 239_100, 284_700, 335_000,
              366_000, 364_700, 319_700, 256_800, 202_700, 173_400]
IMPROVEMENT_MONTH = 4                     # 4 月起冰水主機改為變頻並調整冰水出水溫度


def fit():
    slope, intercept = linear_regression(BASE_CDD, BASE_KWH)
    predicted = [intercept + slope * x for x in BASE_CDD]
    residuals = [y - p for y, p in zip(BASE_KWH, predicted)]
    r2 = correlation(BASE_CDD, BASE_KWH) ** 2
    cv_rmse = (fmean(r * r for r in residuals) ** 0.5) / fmean(BASE_KWH)
    return slope, intercept, r2, cv_rmse


if __name__ == "__main__":
    slope, intercept, r2, cv = fit()
    print(f"基線模型：kWh = {intercept:,.0f} + {slope:,.1f} × CDD")
    print(f"R² = {r2:.3f}，CV(RMSE) = {cv:.1%}")
    cusum = 0.0
    total_expected = total_actual = 0.0
    print("月  CDD  預期 kWh   實際 kWh   差值      CUSUM")
    for m, (cdd, kwh) in enumerate(zip(REPORT_CDD, REPORT_KWH), start=1):
        expected = intercept + slope * cdd
        diff = kwh - expected
        cusum += diff
        total_expected += expected
        total_actual += kwh
        mark = " ← 改善上線" if m == IMPROVEMENT_MONTH else ""
        print(f"{m:>2} {cdd:>4} {expected:>10,.0f} {kwh:>10,} {diff:>+9,.0f} {cusum:>+10,.0f}{mark}")
    saved = total_expected - total_actual
    print(f"報告期正規化節能量：{saved:,.0f} kWh（{saved / total_expected:.1%}）")
    raw = sum(BASE_KWH) - sum(REPORT_KWH)
    print(f"若直接比較兩年用電：{raw:,.0f} kWh（{raw / sum(BASE_KWH):.1%}），報告期較熱，低估了改善")
