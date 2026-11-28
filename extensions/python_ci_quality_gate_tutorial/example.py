"""品質閘門判定：依變更風險決定必過項目，並以成品雜湊確認測試的是同一份成品（標準函式庫）。"""
import hashlib

GATES = {   # 風險等級: 必過項目
    "docs": ["lint"],
    "normal": ["lint", "typecheck", "unit"],
    "control": ["lint", "typecheck", "unit", "integration", "manual_review"],
}


def risk_of(changed_files):
    if any(f.startswith(("src/bms/control/", "src/bms/write/")) for f in changed_files):
        return "control"                    # 會寫入設備的程式碼
    if all(f.endswith((".md", ".txt")) for f in changed_files):
        return "docs"
    return "normal"


def decide(changed, results, built_hash, tested_hash):
    risk = risk_of(changed)
    missing = [g for g in GATES[risk] if results.get(g) is None]
    failed = [g for g in GATES[risk] if results.get(g) is False]
    if built_hash != tested_hash:
        return risk, "阻擋：測試的成品與要部署的成品雜湊不同"
    if failed:
        return risk, f"阻擋：{failed} 未通過"
    if missing:
        return risk, f"阻擋：{missing} 尚未執行"
    return risk, "通過，可以部署"


if __name__ == "__main__":
    wheel = b"bmsgateway-2.4.1-py3-none-any.whl contents"
    h = hashlib.sha256(wheel).hexdigest()
    tampered = hashlib.sha256(wheel + b" patched").hexdigest()
    cases = [
        ("只改文件", ["README.md"], {"lint": True}, h),
        ("一般程式", ["src/bms/report.py"], {"lint": True, "typecheck": True, "unit": True}, h),
        ("控制程式缺審查", ["src/bms/control/setpoint.py"],
         {"lint": True, "typecheck": True, "unit": True, "integration": True}, h),
        ("單元測試失敗", ["src/bms/report.py"], {"lint": True, "typecheck": True, "unit": False}, h),
        ("成品被替換", ["src/bms/report.py"], {"lint": True, "typecheck": True, "unit": True}, tampered),
    ]
    for name, changed, results, tested in cases:
        risk, verdict = decide(changed, results, h, tested)
        print(f"{name:<10} 風險 {risk:<7} → {verdict}")
