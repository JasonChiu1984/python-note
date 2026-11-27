"""Python 3.15 新語法實測：推導式解包（PEP 798）、frozendict、sentinel、re.prefixmatch()。需 Python 3.15。"""
import copy
import pickle
import re

MISSING = sentinel("MISSING")       # 模組層級定義，pickle／copy 後仍是同一個物件

racks = [["AHU-01", "AHU-02"], ["CH-01"], [], ["CT-01", "CT-02"]]
print("攤平：", [*r for r in racks])
defaults = [{"scale": 1.0}, {"unit": "degC"}, {"scale": 0.1}]
print("合併（後者覆蓋前者）：", {**d for d in defaults})
print("集合（排序後顯示）：", sorted({*r for r in racks}))

limits = frozendict(AHU=(5.0, 40.0), CH=(3.0, 15.0))
print("frozendict 可雜湊：", hash(limits) == hash(frozendict(CH=(3.0, 15.0), AHU=(5.0, 40.0))))


def update_setpoint(value=MISSING):
    if value is MISSING:
        return "未提供 → 保持原值"
    if value is None:
        return "None → 清除設定點"
    return f"設為 {value}"


for v in (MISSING, None, 7.0):
    print(f"{v!r:<8} {update_setpoint(v)}")
print("pickle/copy 身分不變：", pickle.loads(pickle.dumps(MISSING)) is MISSING, copy.deepcopy(MISSING) is MISSING)

print("prefixmatch：", bool(re.prefixmatch(r"AHU-\d+", "AHU-01/SAT")), bool(re.prefixmatch(r"SAT", "AHU-01/SAT")))
print("與 re.match 相同語意，但名稱不再讓人誤以為會比對整串")
