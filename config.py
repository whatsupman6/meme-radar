"""全局配置。§7 标注为 UNVERIFIED 的项必须先跑 verify_sources.py 确认。"""

# ---- GeckoTerminal network id ----
# 已实测: "bsc"、"robinhood" 均返回正常数据
# UNVERIFIED: solana 的 id，预检脚本会从 /networks 列表解析并打印，回填后再用
GT_NETWORKS = {
    "bsc": "bsc",
    "robinhood": "robinhood",
    "solana": "solana",   # <-- 预检确认
}

# ---- DexScreener chainId ----（预检会用真实返回校验）
DS_CHAIN = {"bsc": "bsc", "robinhood": "robinhood", "solana": "solana"}

# ---- 区块浏览器 ----
# robinhood 的 Blockscout 来自教程原文，已确认；
# UNVERIFIED: BSC / Solana 浏览器域名我未在本次调研中实测，部署前自行打开确认一次
EXPLORER = {
    "bsc":       "",   # 例如填你惯用的 BSC 浏览器 token 页前缀
    "solana":    "",   # 例如填你惯用的 Solana 浏览器 token 页前缀
    "robinhood": "https://robinhoodchain.blockscout.com/address/",
}

# ---- 每轮预算，防止触发限速 ----
MAX_SECURITY_CALLS_PER_RUN = 40     # 安全检测总次数上限
MAX_PUSH_PER_RUN = 6                # 单轮最多推几条，防刷屏
PUSH_SCORE_MIN = 60                 # 推送分数线

# ---- 请求间隔（秒），按最保守的限速反推 ----
MIN_INTERVAL = {
    "api.geckoterminal.com": 6.5,   # ≈9 calls/min，卡在 10/min 之下
    "api.dexscreener.com":   0.25,  # 300/min
    "api.gopluslabs.io":     1.0,   # 官方未给明确限速，保守
    "api.honeypot.is":       1.0,
    "api.rugcheck.xyz":      1.0,
}

# ---- 跟踪与复盘 ----
FOLLOWUP_HOURS = [1, 2, 4, 8, 24]   # 快照时点
TRACK_MAX = 300                     # 同时跟踪的候选上限
SEEN_TTL_HOURS = 48                 # 去重记忆保留时长
