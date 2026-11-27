"""多來源設定合併：預設值 < 設定檔 < 環境變數，記錄每個值的來源，必填缺漏或型別錯誤時啟動即失敗（標準函式庫）。"""
import json

SCHEMA = {   # 名稱: (型別, 必填, 預設值, 是否敏感)
    "MODBUS_HOST": (str, True, None, False),
    "MODBUS_PORT": (int, False, 502, False),
    "POLL_SECONDS": (float, False, 5.0, False),
    "DB_PASSWORD": (str, True, None, True),
    "WRITE_ENABLED": (bool, False, False, False),
}


def parse(typ, raw):
    if typ is bool:
        if str(raw).lower() in ("1", "true", "yes"):
            return True
        if str(raw).lower() in ("0", "false", "no"):
            return False
        raise ValueError(f"無法解讀為布林值：{raw!r}")
    return typ(raw)


def load(file_cfg: dict, env: dict):
    values, sources, errors = {}, {}, []
    for key, (typ, required, default, _) in SCHEMA.items():
        for src, layer in (("env", env), ("file", file_cfg)):
            if key in layer:
                try:
                    values[key], sources[key] = parse(typ, layer[key]), src
                except ValueError as e:
                    errors.append(f"{key}（{src}）：{e}")
                break
        else:
            if required:
                errors.append(f"{key} 為必填")
            else:
                values[key], sources[key] = default, "default"
    unknown = (set(file_cfg) | {k for k in env if k.startswith(("MODBUS_", "POLL_", "DB_", "WRITE_"))}) - set(SCHEMA)
    errors += [f"未知設定 {k}（可能是拼錯）" for k in sorted(unknown)]
    if errors:
        raise SystemExit("設定錯誤，拒絕啟動：\n  " + "\n  ".join(errors))
    return values, sources


def evidence(values, sources):
    return {k: ("***" if SCHEMA[k][3] else v, sources[k]) for k, v in values.items()}


if __name__ == "__main__":
    file_cfg = {"MODBUS_HOST": "192.168.10.20", "POLL_SECONDS": "2"}
    env = {"DB_PASSWORD": "s3cret", "MODBUS_PORT": "1502"}
    values, sources = load(file_cfg, env)
    print(json.dumps(evidence(values, sources), ensure_ascii=False))
    try:
        load({"MODBUS_HOST": "192.168.10.20", "POLL_SECOND": "2"}, {"WRITE_ENABLED": "maybe"})
    except SystemExit as e:
        print(e)
