"""從封包時間戳計算 Modbus TCP 回應時間、找出重傳與未回應的交易（標準函式庫）。

輸入模擬 tshark -T fields 的輸出：時間, 方向, 交易 ID, 功能碼。
"""
from statistics import median

ROWS = """\
0.000000,req,1,3
0.018200,resp,1,3
0.500000,req,2,3
0.524900,resp,2,3
1.000000,req,3,3
1.200000,req,3,3
1.231000,resp,3,3
1.500000,req,4,16
2.000000,req,5,3
2.019500,resp,5,131
"""


if __name__ == "__main__":
    reqs, resps = {}, {}
    retrans = []
    for line in ROWS.splitlines():
        t, d, tid, fc = line.split(",")
        t, tid, fc = float(t), int(tid), int(fc)
        if d == "req":
            if tid in reqs:
                retrans.append(tid)
            reqs.setdefault(tid, (t, fc))
        else:
            resps[tid] = (t, fc)
    rtts = {}
    for tid, (t, fc) in reqs.items():
        if tid not in resps:
            print(f"交易 {tid}（FC{fc}）沒有回應")
            continue
        rt, rfc = resps[tid]
        rtts[tid] = (rt - t) * 1000
        note = f"  ← 例外回應（FC{rfc} = 0x80 + {rfc - 128}）" if rfc >= 128 else ""
        print(f"交易 {tid} FC{fc}：{rtts[tid]:.1f} ms{note}")
    print(f"重傳的交易：{retrans}（回應時間以第一次請求計，包含了重傳等待）")
    print(f"回應時間中位數 {median(rtts.values()):.1f} ms，最大 {max(rtts.values()):.1f} ms")
