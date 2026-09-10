import os, time
import core.sources as S
import core.store as St
from core.security import check
from core.rules import CFG, prefilter, score
from core.tg import send, E
from config import (MAX_SECURITY_CALLS_PER_RUN, MAX_PUSH_PER_RUN,
                    PUSH_SCORE_MIN, SEEN_TTL_HOURS, TRACK_MAX, EXPLORER)

THREAD = os.environ.get("TG_THREAD_SCAN")


def card(v, sec, sc, why):
    risks = "、".join(sec["risks"]) if sec["risks"] else "未发现硬风险"
    lines = [
        f"🔎 <b>{E(v['name'])}</b> · {v['chain']} · {E(v['dex'])}",
        f"评分 <b>{sc}</b>/100 ｜ 年龄 {v['age_min']:.0f}m ｜ {' / '.join(why) or '-'}",
        f"池 ${v['liq']:,.0f} ｜ 15m量 ${v['v15']:,.0f} ｜ FDV ${v['fdv']:,.0f}",
        f"15m 买{v['buys']}/卖{v['sells']}（买家{v['buyers']}·卖家{v['sellers']}）",
        f"⚠️ {E(risks)}",
    ]
    if sec["notes"]:
        lines.append(E(" / ".join(sec["notes"])))
    lines += [
        f"<code>{v['base']}</code>",
        f"📊 https://dexscreener.com/{v['chain']}/{v['base']}",
    ]
    if EXPLORER.get(v["chain"]):
        lines.append(f"🔗 {EXPLORER[v['chain']]}{v['base']}")
    return "\n".join(lines)


def main():
    seen = St.load_seen(SEEN_TTL_HOURS)
    track = St.load_track()
    budget = MAX_SECURITY_CALLS_PER_RUN
    hits, stats = [], {"total": 0, "new": 0, "passed": 0, "reasons": {}}

    for chain in CFG:
        for p in S.gt_new_pools(chain):
            try:
                v = S.pool_view(p, chain)
            except Exception as e:
                print(f"[warn] pool_view: {e}")
                continue
            stats["total"] += 1
            key = f"{chain}:{v['pool']}"
            if key in seen:
                continue
            stats["new"] += 1
            reason = prefilter(v)
            if reason:
                stats["reasons"][reason] = stats["reasons"].get(reason, 0) + 1
                seen[key] = time.time()
                continue
            if budget <= 0:
                print("[info] 安全检测预算耗尽，本轮剩余留给下一轮")
                break
            budget -= 1
            sec = check(chain, v["base"])
            sc, why = score(v, sec)
            seen[key] = time.time()
            stats["passed"] += 1
            St.append(St.CAND, {"ts": time.time(), "v": v, "sec": sec,
                                "score": sc, "why": why})
            if sc >= PUSH_SCORE_MIN and not sec["blocking"]:
                hits.append((v, sec, sc, why))
                if sec.get("ds_pair"):
                    track[key] = {"t0": time.time(), "chain": chain,
                                  "ds_pair": sec["ds_pair"], "base": v["base"],
                                  "name": v["name"], "dex": v["dex"],
                                  "liq0": v["liq"], "price0": v["price"],
                                  "score": sc, "snaps": {}, "done": False}

    hits.sort(key=lambda x: -x[2])
    for v, sec, sc, why in hits[:MAX_PUSH_PER_RUN]:
        send(card(v, sec, sc, why), THREAD)

    St.save_seen(seen)
    St.save_track(track, TRACK_MAX)
    print(f"[stats] 扫到{stats['total']} 新{stats['new']} 过初筛{stats['passed']} "
          f"推送{min(len(hits), MAX_PUSH_PER_RUN)}")
    print(f"[stats] 淘汰原因 {stats['reasons']}")


if __name__ == "__main__":
    main()
