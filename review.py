"""跑够 48h 后执行：python review.py
统计哪些初筛维度真的和 alive 相关，据此改 rules.py 的阈值和 WEIGHTS。"""
from collections import defaultdict
import core.store as St


def bucket(v, edges):
    for e in edges:
        if v < e:
            return f"<{e:,.0f}"
    return f">={edges[-1]:,.0f}"


def table(title, groups):
    print(f"\n--- {title} ---")
    print(f"{'组':<22}{'样本':>6}{'alive%':>9}{'rug%':>8}{'均峰值':>9}")
    for k, rows in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        n = len(rows)
        if n < 3:
            continue
        a = sum(1 for r in rows if r["label"] == "alive") / n * 100
        rg = sum(1 for r in rows if r["label"] == "rug_like") / n * 100
        pk = sum(r.get("peak_x", 0) for r in rows) / n
        print(f"{str(k):<22}{n:>6}{a:>8.0f}%{rg:>7.0f}%{pk:>9.2f}")


def main():
    rows = [r for r in St.read_jsonl(St.OUT) if r.get("label") != "unknown"]
    print(f"结算样本 {len(rows)} 条")
    if len(rows) < 20:
        print("样本太少，先让系统多跑几天再来调参")
        return

    for name, keyfn in (
        ("按链", lambda r: r["chain"]),
        ("按 dex", lambda r: r["dex"]),
        ("按初始流动性", lambda r: bucket(r["liq0"], [5000, 15000, 50000])),
        ("按初评分数", lambda r: bucket(r["score"], [65, 75, 85])),
    ):
        g = defaultdict(list)
        for r in rows:
            g[keyfn(r)].append(r)
        table(name, g)

    print("\n调参建议读法：")
    print("· 某个 dex / 流动性区间 rug% 明显偏高 → 提高该链 liq_min 或把 dex 移出白名单")
    print("· 高分组 alive% 没有比低分组高 → WEIGHTS 权重没抓到真信号，减掉无效项")
    print("· 淘汰原因分布看 scan 日志：占比最大的那条决定了你实际在过滤什么")


if __name__ == "__main__":
    main()
