"""以參數清單（不經 shell）組出 docker run 指令，並在組裝前驗證輸入（標準函式庫）。

subprocess.run(argv) 直接執行參數清單，不會被名稱中的空白、分號或 $() 注入指令。
範例只印出指令，不實際執行 Docker。
"""
import re
import shlex

NAME_RE = re.compile(r"[a-z0-9][a-z0-9_.-]{0,62}")
IMAGE_RE = re.compile(r"[a-z0-9./_-]+(:[A-Za-z0-9._-]+|@sha256:[0-9a-f]{64})")


def build_run(name, image, data_dir, *, memory="256m", cpus="0.5"):
    if not NAME_RE.fullmatch(name):
        raise ValueError(f"容器名稱不合法：{name!r}")
    if not IMAGE_RE.fullmatch(image) or image.endswith(":latest"):
        raise ValueError(f"映像必須帶明確版本或 digest：{image!r}")
    if not data_dir.startswith("/srv/bms/"):
        raise ValueError(f"只允許掛載 /srv/bms/ 底下的目錄：{data_dir!r}")
    return ["docker", "run", "-d", "--name", name,
            "--user", "10001:10001", "--read-only", "--tmpfs", "/tmp",
            "--memory", memory, "--cpus", cpus, "--restart", "unless-stopped",
            "--health-cmd", "python -m app.health", "--health-interval", "30s",
            "-v", f"{data_dir}:/data:ro", image]


if __name__ == "__main__":
    argv = build_run("modbus-poller", "bms/poller:2.4.1", "/srv/bms/poller")
    print("argv 清單：", argv[:6], "…")
    print("對應的 shell 指令（僅供閱讀）：")
    print(" ", shlex.join(argv))
    for bad in [("poller; rm -rf /", "bms/poller:2.4.1", "/srv/bms/x"),
                ("poller", "bms/poller:latest", "/srv/bms/x"),
                ("poller", "bms/poller:2.4.1", "/etc")]:
        try:
            build_run(*bad)
        except ValueError as e:
            print("拒絕：", e)
