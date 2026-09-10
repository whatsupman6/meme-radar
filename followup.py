"""按 config.FOLLOWUP_HOURS 给被推送过的候选打快照，24h 后定标签。
快照走 DexScreener 批量端点（300/min），比逐个查 GT 省得多。"""
import os, time
import core.sources as S
import core.store as St
from core.tg import send, E
from config import FOLLOWUP_HOURS, TRACK_MAX

THREAD = os.environ.get("TG_THREAD_SCAN")


def label(t):
    snaps = t["snaps"]
    s24 = snaps.get("24")
    if not s24:
        return "unknown", 0.0
    liq0 = max(t["liq0"], 1)
    p0 = max(t["price0"], 1e-18)
    peak = max([s["price"] for s in snaps.values() if s.get("price")] + [p0])
    peak_x = peak / p0
    if s24["liq"] < liq0 * 0.5:
        return "rug_like", peak_x
    if s24["v24"] < liq0 * 0.5 and s24["price"] < p0:
        return "dead", peak_x
    if s24["liq"] >= liq0 and s24["price"] >= p0 * 1.5:
        return "alive", peak_x
    return "flat", peak_x


def main():
    track = St.load_track()
    if not track:
        print("[info] 无跟踪对象"); return

    by_chain, due = {}, {}
    now = time.time()
    for key, t in track.items():
        if t.get("done"):
            continue
        hrs = (now - t["t0"]) / 3600
        want = [h for h in FOLLOWUP_HOURS
                if hrs >= h and str(h) not in t["snaps"]]
        if want:
            due[key] = max(want)
            by_chain.setdefault(t["chain"], []).append(t["ds_pair"])

    if not due:
        print("[info] 本轮无到期快照"); return

    snapshots = {}
    for chain, addrs in by_chain.items():
        snapshots[chain] = S.ds_pairs_batch(chain, list(set(addrs)))

    finalized = []
    for key, h in due.items():
        t = track[key]
        p = (snapshots.get(t["chain"]) or {}).get(t["ds_pair"].lower())
        if not p:
            t["snaps"][str(h)] = {"liq": 0.0, "v24": 0.0, "price": 0.0, "gone": True}
        else:
            t["snaps"][str(h)] = {
                "liq": float((p.get("liquidity") or {}).get("usd") or 0),
                "v24": float((p.get("volume") or {}).get("h24") or 0),
                "price": float(p.get("priceUsd") or 0),
                "txns24": (p.get("txns") or {}).get("h24") or {},
            }
        if h == max(FOLLOWUP_HOURS):
            lab, peak_x = label(t)
            t["done"] = True
            St.append(St.OUT, {"key": key, "chain": t["chain"], "name": t["name"],
                               "base": t["base"], "dex": t["dex"],
                               "score": t["score"], "liq0": t["liq0"],
                               "label": lab, "peak_x": round(peak_x, 2),
                               "snaps": t["snaps"], "t0": t["t0"]})
            finalized.append((t, lab, peak_x))

    St.save_track(track, TRACK_MAX)

    if finalized:
        good = [f for f in finalized if f[1] == "alive"]
        lines = [f"📒 <b>24h 复盘</b>（{len(finalized)} 个结算）",
                 f"alive {len(good)} ｜ "
                 f"flat {sum(1 for f in finalized if f[1]=='flat')} ｜ "
                 f"dead {sum(1 for f in finalized if f[1]=='dead')} ｜ "
                 f"rug {sum(1 for f in finalized if f[1]=='rug_like')}"]
        for t, lab, px in sorted(finalized, key=lambda x: -x[2])[:8]:
            lines.append(f"· {E(t['name'])} [{lab}] 峰值 {px:.1f}x 初评{t['score']}")
        send("\n".join(lines), THREAD)
    print(f"[stats] 快照 {len(due)}，结算 {len(finalized)}")


if __name__ == "__main__":
    main()
