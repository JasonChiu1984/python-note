"""機房能效：PUE、partial PUE、WUE 與年度累計，並示範用瞬時值與能量值計算 PUE 的差異（標準函式庫）。"""

# 每月能量（MWh）與用水（m3）：IT、冷卻、配電損失、照明與其他
MONTHS = [
    # (IT, 冷卻, 配電損失, 其他, 用水)
    (720, 180, 43, 12, 2100), (650, 150, 39, 11, 1800), (720, 185, 43, 12, 2300),
    (700, 215, 42, 12, 2900), (730, 265, 44, 12, 3800), (710, 300, 43, 12, 4600),
    (735, 330, 44, 12, 5200), (735, 335, 44, 12, 5300), (710, 290, 43, 12, 4400),
    (725, 240, 43, 12, 3300), (705, 195, 42, 12, 2500), (725, 180, 43, 12, 2200),
]


if __name__ == "__main__":
    it = sum(m[0] for m in MONTHS)
    total = sum(sum(m[:4]) for m in MONTHS)
    cooling = sum(m[1] for m in MONTHS)
    water = sum(m[4] for m in MONTHS)
    print(f"年度 PUE = {total:,} ÷ {it:,} = {total / it:.3f}")
    print(f"冷卻 partial PUE = ({it:,} + {cooling:,}) ÷ {it:,} = {(it + cooling) / it:.3f}")
    print(f"WUE = {water:,} m3 ÷ {it:,} MWh = {water * 1000 / (it * 1000):.2f} L/kWh")
    monthly = [sum(m[:4]) / m[0] for m in MONTHS]
    print("各月 PUE：", [round(p, 2) for p in monthly])
    print(f"各月 PUE 算術平均 {sum(monthly) / 12:.4f}，年度 PUE {total / it:.4f}：此例 IT 負載穩定所以接近；IT 負載季節變化大時兩者會明顯不同，年度值應以能量加總計算")
    peak_it_kw, peak_total_kw = 1050, 1680                   # 夏季某時刻的瞬時功率
    print(f"夏季尖峰瞬時 PUE = {peak_total_kw / peak_it_kw:.2f}，不能代表年度值")
