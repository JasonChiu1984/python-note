"""設定檔完整性簽章（HMAC-SHA256＋金鑰版本）與密碼雜湊（scrypt），只用標準函式庫。

情境：閘道器從維護主機下載 Modbus 點位設定檔。要確認檔案沒被竄改、來自持有金鑰的一方，
並能在金鑰輪替期間同時接受新舊金鑰。這只提供完整性與來源驗證，不提供機密性（不加密）。
"""
import base64
import hashlib
import hmac
import json

KEYS = {                                   # 實務上金鑰放在 KMS／HSM 或受保護的檔案，不寫進程式
    "k2025": bytes.fromhex("11" * 32),
    "k2026": bytes.fromhex("22" * 32),
}
ACTIVE_KID = "k2026"
ACCEPTED_KIDS = {"k2025", "k2026"}         # 輪替期間兩把都接受；過渡期結束後移除 k2025


def canonical(obj) -> bytes:
    """固定鍵順序與分隔字元，避免同內容不同排版導致簽章不同。"""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sign(config: dict, kid: str = ACTIVE_KID) -> dict:
    mac = hmac.new(KEYS[kid], kid.encode() + b"." + canonical(config), hashlib.sha256).digest()
    return {"kid": kid, "config": config, "mac": base64.urlsafe_b64encode(mac).decode()}


def verify(envelope: dict) -> dict:
    kid = envelope.get("kid")
    if kid not in ACCEPTED_KIDS:
        raise ValueError(f"不接受的金鑰版本：{kid}")
    expected = hmac.new(KEYS[kid], kid.encode() + b"." + canonical(envelope["config"]),
                        hashlib.sha256).digest()
    given = base64.urlsafe_b64decode(envelope["mac"])
    if not hmac.compare_digest(expected, given):       # 常數時間比較，避免時序側通道
        raise ValueError("簽章不符：檔案可能被修改")
    return envelope["config"]


def hash_password(password: str, salt: bytes) -> str:
    dk = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt$16384$8$1${salt.hex()}${dk.hex()}"


def check_password(password: str, stored: str) -> bool:
    _, n, r, p, salt_hex, dk_hex = stored.split("$")
    dk = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex),
                        n=int(n), r=int(r), p=int(p), dklen=len(dk_hex) // 2)
    return hmac.compare_digest(dk.hex(), dk_hex)


if __name__ == "__main__":
    config = {"device": "AHU-01", "unit_id": 3,
              "points": [{"name": "SAT", "fc": 3, "addr": 0, "scale": 0.1}]}
    env = sign(config)
    print("簽章：", env["kid"], env["mac"][:16] + "…")
    print("驗證原檔：", verify(env)["device"])

    tampered = json.loads(json.dumps(env))
    tampered["config"]["points"][0]["scale"] = 1.0       # 有人把倍率改成 1.0
    try:
        verify(tampered)
    except ValueError as e:
        print("驗證竄改檔：", e)

    old = sign(config, "k2025")
    print("舊金鑰簽的檔案（輪替期內）：", verify(old)["unit_id"])
    ACCEPTED_KIDS.discard("k2025")
    try:
        verify(old)
    except ValueError as e:
        print("過渡期結束後：", e)

    salt = bytes.fromhex("a1" * 16)                       # 示範固定 salt；實務用 os.urandom(16)
    stored = hash_password("Bms#2026!", salt)
    print("密碼雜湊：", stored[:40] + "…")
    print("正確密碼：", check_password("Bms#2026!", stored), "／錯誤密碼：", check_password("bms#2026!", stored))
