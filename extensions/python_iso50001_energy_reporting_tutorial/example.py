"""以冷房度日（CDD）建立能源基線、計算正規化節能量與 CUSUM（標準函式庫）。

基線期 12 個月：月用電 kWh 對 CDD 做線性迴歸。報告期把實際 CDD 代入基線模型，
得到「如果沒有改善會用多少電」，再與實際用電相減。CUSUM 累計「實際 − 預期」，斜率轉負是回查變動的線索，不單獨證明因果。
"""
from math import sqrt
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


def regression_intervals(x, y, x_new, t_critical):
    """OLS with intercept: mean-response CI and single-observation PI."""
    n = len(x)
    if n < 3 or len(y) != n:
        raise ValueError("至少需要三組成對且非固定 CDD 的觀測值")
    slope, intercept = linear_regression(x, y)
    x_bar = fmean(x)
    sxx = sum((v - x_bar) ** 2 for v in x)
    sse = sum((vy - (intercept + slope * vx)) ** 2 for vx, vy in zip(x, y))
    s = sqrt(sse / (n - 2))
    h = 1 / n + (x_new - x_bar) ** 2 / sxx
    estimate = intercept + slope * x_new
    half_ci, half_pi = t_critical * s * sqrt(h), t_critical * s * sqrt(1 + h)
    return (estimate - half_ci, estimate + half_ci), (estimate - half_pi, estimate + half_pi)


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
    # Only for this 12-point, 95% two-sided example: t(0.975, df=10).
    ci, pi = regression_intervals(BASE_CDD, BASE_KWH, REPORT_CDD[3], 2.228139)
    print(f"4 月 95% 平均反應信賴區間：{ci[0]:,.0f}–{ci[1]:,.0f} kWh")
    print(f"4 月 95% 單月預測區間：{pi[0]:,.0f}–{pi[1]:,.0f} kWh")
