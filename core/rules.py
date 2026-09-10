"""把三篇教程里的人工 checklist 代码化。阈值第一版一定太吵，靠 review.py 迭代。"""

BAD_WORDS = ("official", "airdrop", "presale", "claim", "reward",
             "空投", "预售", "领取")

CFG = {
    "bsc": {
        "age_max": 45, "liq_min": 8000, "v15_min": 3000,
        "min_buyers": 5, "dex_allow": None,
    },
    "solana": {
        "age_max": 45, "liq_min": 8000, "v15_min": 3000,
        "min_buyers": 5, "dex_allow": None,
    },
    # 第二篇核心结论：Pons V2 有反狙击/毕业机制，优先只看白名单 dex；
    # 白名单 id 来自 GT 实测返回（robinhood 新池里出现 pons-v2 / uniswap-v4-robinhood）
    "robinhood": {
        "age_max": 60, "liq_min": 3000, "v15_min": 800,
        "min_buyers": 4, "dex_allow": ("pons-v2", "uniswap-v4-robinhood"),
    },
}


def prefilter(v: dict) -> str | None:
    """返回 None = 通过；返回字符串 = 淘汰原因。"""
    c = CFG[v["chain"]]
    if v["age_min"] > c["age_max"]:
        return "太老"
    if v["age_min"] < 2:
        return "太新，数据不足"                      # 避免抓到 1 分钟的诱饵
    if c["dex_allow"] and v["dex"] not in c["dex_allow"]:
        return f"dex={v['dex']} 非白名单"
    if v["liq"] < c["liq_min"]:
        return "流动性不足"
    if v["v15"] < c["v15_min"]:
        return "15m 量不足"
    if v["sells"] == 0:
        return "只有买没有卖（可能卖不出/对倒）"       # 第一篇红线
    if v["buyers"] < c["min_buyers"]:
        return "买家地址太少"
    if v["v15"] > v["liq"] * 8:
        return "量/池比异常，疑似对倒"
    if v["fdv"] and v["liq"] and v["fdv"] / v["liq"] > 400:
        return "FDV/流动性 严重失衡"                  # 第二篇：有价无市
    low = v["name"].lower()
    if any(w in low for w in BAD_WORDS):
        return "命名红线"
    return None


WEIGHTS = {
    "liq_thick": 10, "vol_healthy": 10, "two_way": 10,
    "buyers_wide": 8, "dex_bonus": 8, "socials": 6, "holders": 6,
    "risk_penalty": 12,
}


def score(v: dict, sec: dict) -> tuple[int, list[str]]:
    s, why = 50, []
    W = WEIGHTS
    if v["liq"] >= 30000:
        s += W["liq_thick"]; why.append("池子较厚")
    ratio = v["v15"] / max(v["liq"], 1)
    if 0.3 <= ratio <= 3:
        s += W["vol_healthy"]; why.append("量/池健康")
    if v["buys"] and v["sells"] and 0.4 <= v["sells"] / v["buys"] <= 2.5:
        s += W["two_way"]; why.append("买卖双向")
    if v["buyers"] >= 15:
        s += W["buyers_wide"]; why.append("买家分散")
    if v["dex"] == "pons-v2":
        s += W["dex_bonus"]; why.append("Pons V2")
    if sec.get("socials"):
        s += W["socials"]; why.append("有社交")
    if sec.get("holders") and sec["holders"] >= 200:
        s += W["holders"]; why.append("持有人>200")
    n = len(sec.get("risks") or [])
    if n:
        s -= W["risk_penalty"] * n
    if sec.get("blocking"):
        s = min(s, 10)
    return max(0, min(100, s)), why
