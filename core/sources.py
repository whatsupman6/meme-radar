from datetime import datetime, timezone
from core.http import get_json
from config import GT_NETWORKS, DS_CHAIN

GT = "https://api.geckoterminal.com/api/v2"
DS = "https://api.dexscreener.com"


# ---------- 发现层：GeckoTerminal ----------
def gt_networks(max_pages: int = 20):
    """预检用：列出所有可用 network id。
    按响应里的 links.next 翻页（API 自己告诉最后一页），不用试探到报错为止。"""
    ids, page = [], 1
    while page <= max_pages:
        d = get_json(f"{GT}/networks", {"page": page})
        if not d:
            break
        ids.extend(x["id"] for x in d.get("data", []))
        if not ((d.get("links") or {}).get("next")):
            break
        page += 1
    return ids


def gt_new_pools(chain_key: str, page: int = 1):
    net = GT_NETWORKS[chain_key]
    d = get_json(f"{GT}/networks/{net}/new_pools", {"page": page})
    return (d or {}).get("data", [])


def pool_view(p: dict, chain_key: str) -> dict:
    """把 GT 池子对象压平成统一视图（字段名按实测返回结构）。"""
    a, rel = p["attributes"], p["relationships"]
    created = datetime.fromisoformat(a["pool_created_at"].replace("Z", "+00:00"))
    tx15 = (a.get("transactions") or {}).get("m15") or {}
    f = lambda v: float(v) if v not in (None, "") else 0.0
    return {
        "chain": chain_key,
        "pool": a["address"],
        "name": a.get("name") or "",
        "dex": rel["dex"]["data"]["id"],
        "base": rel["base_token"]["data"]["id"].split("_", 1)[1],
        "quote": rel["quote_token"]["data"]["id"].split("_", 1)[1],
        "created_at": a["pool_created_at"],
        "age_min": (datetime.now(timezone.utc) - created).total_seconds() / 60,
        "liq": f(a.get("reserve_in_usd")),
        "fdv": f(a.get("fdv_usd")),
        "mcap": f(a.get("market_cap_usd")),
        "price": f(a.get("base_token_price_usd")),
        "v15": f((a.get("volume_usd") or {}).get("m15")),
        "buys": tx15.get("buys", 0),
        "sells": tx15.get("sells", 0),
        "buyers": tx15.get("buyers", 0),
        "sellers": tx15.get("sellers", 0),
    }


# ---------- 行情/社交层：DexScreener ----------
def ds_token_pairs(chain_key: str, token: str):
    return get_json(f"{DS}/token-pairs/v1/{DS_CHAIN[chain_key]}/{token}") or []


def ds_search(q: str):
    d = get_json(f"{DS}/latest/dex/search", {"q": q})
    return (d or {}).get("pairs", []) or []


def ds_pairs_batch(chain_key: str, pair_addrs: list[str]):
    """批量拉 pair 快照。DexScreener 该端点文档标注支持一个或多个地址，限速 300/min。"""
    out = {}
    for i in range(0, len(pair_addrs), 20):
        chunk = ",".join(pair_addrs[i:i + 20])
        d = get_json(f"{DS}/latest/dex/pairs/{DS_CHAIN[chain_key]}/{chunk}")
        pairs = (d or {}).get("pairs") or (d if isinstance(d, list) else []) or []
        for p in pairs:
            if p and p.get("pairAddress"):
                out[p["pairAddress"].lower()] = p
    return out


# ---------- 安全层 ----------
def goplus_evm(chain_id: str, addr: str) -> dict:
    d = get_json(f"https://api.gopluslabs.io/api/v1/token_security/{chain_id}",
                 {"contract_addresses": addr})
    res = ((d or {}).get("result") or {})
    return res.get(addr.lower()) or (next(iter(res.values()), {}) if res else {})


def goplus_sol(mint: str) -> dict:
    d = get_json("https://api.gopluslabs.io/api/v1/solana/token_security",
                 {"contract_addresses": mint})
    res = ((d or {}).get("result") or {})
    return res.get(mint) or (next(iter(res.values()), {}) if res else {})


def honeypot_bsc(addr: str) -> dict:
    return get_json("https://api.honeypot.is/v2/IsHoneypot",
                    {"address": addr, "chainID": 56}) or {}


def rugcheck(mint: str) -> dict:
    return get_json(f"https://api.rugcheck.xyz/v1/tokens/{mint}/report/summary") or {}
