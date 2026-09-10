import core.sources as S


def _socials(chain_key, ca):
    """返回 (有无社交, DexScreener pair 地址, DexScreener 快照)"""
    pairs = S.ds_token_pairs(chain_key, ca)
    if not pairs:
        return False, None, None
    pairs = [p for p in pairs if p]
    pairs.sort(key=lambda p: -( (p.get("liquidity") or {}).get("usd") or 0 ))
    top = pairs[0]
    info = top.get("info") or {}
    has = bool(info.get("socials") or info.get("websites"))
    return has, top.get("pairAddress"), top


def check(chain_key: str, ca: str) -> dict:
    """统一安全视图。blocking=True 表示硬红线，直接不推。"""
    out = {"risks": [], "notes": [], "blocking": False,
           "socials": False, "ds_pair": None, "holders": None}

    out["socials"], out["ds_pair"], _ = _socials(chain_key, ca)

    if chain_key == "bsc":
        g = S.goplus_evm("56", ca)
        flags = (("is_honeypot", "貔貅", True), ("cannot_sell_all", "不能全卖", True),
                 ("is_blacklisted", "黑名单", False), ("is_mintable", "可增发", False),
                 ("can_take_back_ownership", "可收回owner", False),
                 ("transfer_pausable", "可暂停转账", False),
                 ("is_proxy", "代理合约可升级", False),
                 ("hidden_owner", "隐藏owner", True))
        for k, label, blocking in flags:
            if g.get(k) == "1":
                out["risks"].append(label)
                if blocking:
                    out["blocking"] = True
        try:
            if float(g.get("owner_percent") or 0) > 0.15:
                out["risks"].append("owner 持仓>15%")
            if float(g.get("creator_percent") or 0) > 0.15:
                out["risks"].append("创建者持仓>15%")
        except ValueError:
            pass
        if g.get("is_open_source") == "0":
            out["risks"].append("合约未开源")

        h = S.honeypot_bsc(ca)
        if (h.get("honeypotResult") or {}).get("isHoneypot"):
            out["risks"].append("模拟买卖失败")
            out["blocking"] = True
        sim = h.get("simulationResult") or {}
        bt, st = sim.get("buyTax"), sim.get("sellTax")
        if st is not None and st > 10:
            out["risks"].append(f"卖出税 {st}%")
        if st is not None and st > 30:
            out["blocking"] = True
        out["notes"].append(f"税 买{bt if bt is not None else '?'}/卖{st if st is not None else '?'}")
        ha = h.get("holderAnalysis") or {}
        if ha.get("holders"):
            out["holders"] = ha["holders"]
            out["notes"].append(f"持有人 {ha['holders']}")

    elif chain_key == "solana":
        g = S.goplus_sol(ca)
        st = lambda k: (g.get(k) or {}).get("status")
        if st("mintable") == "1":
            out["risks"].append("mint 权限未弃")
        if st("freezable") == "1":
            out["risks"].append("可冻结账户")
            out["blocking"] = True
        if st("balance_mutable_authority") == "1":
            out["risks"].append("余额可被改")
            out["blocking"] = True
        if st("metadata_mutable") == "1":
            out["risks"].append("元数据可改")
        if st("transfer_hook_upgradable") == "1":
            out["risks"].append("transfer hook 可改")
        fee = ((g.get("transfer_fee") or {}).get("current_fee_rate") or {}).get("fee_rate")
        if fee:
            try:
                fv = float(fee)
                if fv > 0.05:
                    out["risks"].append(f"转账费 {fv * 100:.1f}%")
                if fv > 0.20:
                    out["blocking"] = True
            except ValueError:
                pass
        if st("transfer_fee_upgradable") == "1":
            out["risks"].append("转账费可上调")

        rc = S.rugcheck(ca)
        for r in (rc.get("risks") or []):
            if r.get("level") == "danger":
                out["risks"].append(r.get("name") or "danger")
        out["notes"].append(
            f"RugCheck {rc.get('score_normalised', '?')}/100，LP锁 {rc.get('lpLockedPct', '?')}%")

    else:  # robinhood
        # 实测：GoPlus 对 RH 链只返回少量字段（is_open_source / cannot_buy 等），
        # 税率字段为空，honeypot.is 不支持该链 → 安全结论主要靠行为指标兜底
        g = S.goplus_evm("4663", ca)
        if g.get("cannot_buy") == "1":
            out["risks"].append("不能买")
            out["blocking"] = True
        if g.get("is_open_source") == "0":
            out["notes"].append("合约未开源(RH 链常见)")
        out["notes"].append("RH 链安全数据有限，务必人工看 Blockscout 持仓/创建者")

    return out
