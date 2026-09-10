"""部署前预检：确认每个免费源可用，并解析出必须回填 config.py 的值。"""
import sys
import core.sources as S
from core.http import get_json
from config import GT_NETWORKS

ok = True


def head(t): print(f"\n=== {t} ===")


head("1) GeckoTerminal network id")
nets = S.gt_networks()
if not nets:
    print("FAIL: 拿不到 network 列表"); ok = False
else:
    print(f"共 {len(nets)} 条链")
    for key, want in GT_NETWORKS.items():
        hit = want in nets
        print(f"  {key:10s} config={want:12s} {'OK' if hit else 'NOT FOUND'}")
        if not hit:
            guess = [n for n in nets if key[:3] in n]
            print(f"     >>> 候选: {guess[:8]}  ← 回填 config.GT_NETWORKS")
            ok = False

head("2) 三链新池抓取")
for key in GT_NETWORKS:
    try:
        pools = S.gt_new_pools(key)
    except Exception as e:
        print(f"  {key}: FAIL {e}"); ok = False; continue
    if not pools:
        print(f"  {key}: 空（可能是 id 错或该链暂无新池）"); continue
    v = S.pool_view(pools[0], key)
    print(f"  {key}: {len(pools)} 个池，样例 {v['name']} dex={v['dex']} "
          f"liq=${v['liq']:,.0f} age={v['age_min']:.1f}m")
    print(f"     dex 分布: {sorted({S.pool_view(p, key)['dex'] for p in pools})}")

head("3) DexScreener chainId 校验")
prof = get_json("https://api.dexscreener.com/token-profiles/latest/v1") or []
print("  最新 profiles 里出现的 chainId:",
      sorted({p.get('chainId') for p in prof if p.get('chainId')}))
print("  ↑ 确认 config.DS_CHAIN 的值在其中（bsc/solana/robinhood）")

head("4) 安全源连通性")
gp = get_json("https://api.gopluslabs.io/api/v1/supported_chains") or {}
ids = {c["id"] for c in gp.get("result", [])}
for want, label in (("56", "BSC"), ("4663", "Robinhood"), ("solana", "Solana")):
    print(f"  GoPlus {label:10s} {'OK' if want in ids else 'MISSING'}")

for key in GT_NETWORKS:
    pools = S.gt_new_pools(key)
    if not pools:
        continue
    ca = S.pool_view(pools[0], key)["base"]
    from core.security import check
    sec = check(key, ca)
    print(f"  security({key}, {ca[:10]}…) risks={sec['risks']} notes={sec['notes']}")

head("结论")
print("PASS，可以进入第 5 步" if ok else "有 FAIL 项，先回填 config.py 再重跑")
sys.exit(0 if ok else 1)
