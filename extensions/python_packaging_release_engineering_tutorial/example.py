"""發行前檢查：版本號符合 PEP 440、版本遞增、wheel 檔名解析與 SHA256SUMS 產生（標準函式庫）。"""
import hashlib
import re

PEP440 = re.compile(r"^(\d+!)?\d+(\.\d+)*((a|b|rc)\d+)?(\.post\d+)?(\.dev\d+)?(\+[a-z0-9.]+)?$", re.I)


def parse(v):
    m = re.match(r"(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?", v)
    nums = tuple(int(x) for x in m.groups()[:3])
    pre = {"a": 0, "b": 1, "rc": 2, None: 3}[m.group(4)]
    return nums + (pre, int(m.group(5) or 0))


def wheel_info(name):
    parts = name[:-4].split("-")
    dist, ver, *rest = parts
    py, abi, plat = rest[-3:]
    return {"套件": dist, "版本": ver, "Python": py, "ABI": abi, "平台": plat}


if __name__ == "__main__":
    for v in ("2.4.1", "2.5.0rc1", "2.5", "v2.5.0", "2.5.0-beta", "2.5.0.post1", "1!2.0"):
        print(f"{v:<12} PEP 440：{'合法' if PEP440.match(v) else '不合法'}")
    released = ["2.4.0", "2.4.1"]
    for cand in ("2.4.1", "2.4.0", "2.5.0rc1", "2.5.0"):
        ok = parse(cand) > parse(released[-1])
        print(f"候選 {cand}：{'可發行' if ok else '拒絕（未大於已發行的 ' + released[-1] + '）'}")
    print("2.5.0rc1 < 2.5.0：", parse("2.5.0rc1") < parse("2.5.0"))
    for w in ("bmsgateway-2.5.0-py3-none-any.whl", "bmsfast-2.5.0-cp313-cp313-manylinux_2_28_x86_64.whl"):
        print(wheel_info(w))
    artifacts = {"bmsgateway-2.5.0-py3-none-any.whl": b"wheel bytes", "bmsgateway-2.5.0.tar.gz": b"sdist bytes"}
    print("SHA256SUMS：")
    for n, data in sorted(artifacts.items()):
        print(f"{hashlib.sha256(data).hexdigest()}  {n}")
