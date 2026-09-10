const DS = "https://api.dexscreener.com";
const UA = { "User-Agent": "meme-ca-bot/1.0" };
const EVM = /\b0x[a-fA-F0-9]{40}\b/;
const SOL = /\b[1-9A-HJ-NP-Za-km-z]{32,44}\b/;

const j = (u) => fetch(u, { headers: UA }).then(r => r.ok ? r.json() : null).catch(() => null);
const esc = (s) => String(s ?? "").replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
const money = (n) => "$" + Math.round(Number(n) || 0).toLocaleString("en-US");

async function evmSec(chain, ca) {
  const risks = [], notes = [];
  const id = chain === "bsc" ? "56" : chain === "robinhood" ? "4663" : null;
  if (!id) return { risks, notes };
  const res = (await j(`https://api.gopluslabs.io/api/v1/token_security/${id}?contract_addresses=${ca}`))?.result || {};
  const g = res[ca.toLowerCase()] || Object.values(res)[0] || {};

  if (chain === "bsc") {
    const map = { is_honeypot: "貔貅", cannot_sell_all: "不能全卖", is_mintable: "可增发",
      transfer_pausable: "可暂停转账", can_take_back_ownership: "可收回owner",
      hidden_owner: "隐藏owner", is_blacklisted: "黑名单" };
    for (const k in map) if (g[k] === "1") risks.push(map[k]);
    if (g.is_open_source === "0") risks.push("未开源");
    if (Number(g.owner_percent) > 0.15) risks.push("owner持仓>15%");
    if (Number(g.creator_percent) > 0.15) risks.push("创建者持仓>15%");
    if (g.holder_count) notes.push(`持有人 ${Number(g.holder_count).toLocaleString()}`);

    const h = await j(`https://api.honeypot.is/v2/IsHoneypot?address=${ca}&chainID=56`);
    if (h?.honeypotResult?.isHoneypot) risks.push("模拟卖出失败");
    const s = h?.simulationResult;
    if (s) {
      notes.push(`真实税 买${s.buyTax ?? "?"}/卖${s.sellTax ?? "?"}`);
      if (Number(s.sellTax) > 10) risks.push(`卖出税 ${s.sellTax}%`);
    }
    if (h?.summary?.risk) notes.push(`honeypot.is 风险:${h.summary.risk}`);
  } else {
    if (g.cannot_buy === "1") risks.push("不能买");
    notes.push(`开源:${g.is_open_source === "1" ? "是" : "否"}`);
    notes.push("RH 链安全数据有限，需人工核验 Blockscout");
  }
  return { risks, notes };
}

async function solSec(ca) {
  const risks = [], notes = [];
  const res = (await j(`https://api.gopluslabs.io/api/v1/solana/token_security?contract_addresses=${ca}`))?.result || {};
  const g = res[ca] || Object.values(res)[0] || {};
  const st = (k) => g?.[k]?.status;
  if (st("mintable") === "1") risks.push("mint权限未弃");
  if (st("freezable") === "1") risks.push("可冻结");
  if (st("balance_mutable_authority") === "1") risks.push("余额可被改");
  if (st("metadata_mutable") === "1") risks.push("元数据可改");
  const fee = Number(g?.transfer_fee?.current_fee_rate?.fee_rate || 0);
  if (fee > 0.05) risks.push(`转账费 ${(fee * 100).toFixed(1)}%`);
  if (st("transfer_fee_upgradable") === "1") risks.push("转账费可上调");

  const rc = await j(`https://api.rugcheck.xyz/v1/tokens/${ca}/report/summary`);
  if (rc) {
    notes.push(`RugCheck ${rc.score_normalised ?? "?"}/100，LP锁 ${rc.lpLockedPct ?? "?"}%`);
    (rc.risks || []).forEach(r => {
      if (r.level === "danger") risks.push(r.name);
      else if (r.level === "warn") notes.push(`⚠${r.name}`);
    });
  }
  return { risks, notes };
}

async function report(ca) {
  const s = await j(`${DS}/latest/dex/search?q=${encodeURIComponent(ca)}`);
  const low = ca.toLowerCase();
  let ps = (s?.pairs || []).filter(p =>
    [p.baseToken?.address, p.quoteToken?.address].some(a => a?.toLowerCase() === low));
  if (!ps.length)
    return `没在 DexScreener 找到 <code>${esc(ca)}</code>\n可能还没被索引（太新），或地址有误。去链上浏览器直接看合约。`;

  ps.sort((a, b) => (b.liquidity?.usd || 0) - (a.liquidity?.usd || 0));
  const p = ps[0], chain = p.chainId;
  const sec = chain === "solana" ? await solSec(ca) : await evmSec(chain, ca);

  const t1 = p.txns?.h1 || {}, t5 = p.txns?.m5 || {};
  const liq = p.liquidity?.usd || 0, mc = p.marketCap || p.fdv || 0;
  const socials = [...(p.info?.socials || []).map(x => x.platform || x.type),
                   ...(p.info?.websites?.length ? ["website"] : [])];
  const ageH = p.pairCreatedAt ? ((Date.now() - p.pairCreatedAt) / 3.6e6).toFixed(1) : "?";

  const flags = [];
  if (liq && mc / liq > 200) flags.push("MC/流动性失衡：有价无市");
  if (t1.sells === 0 && t1.buys > 0) flags.push("1h 只有买没有卖");
  if (liq && (p.volume?.h24 || 0) > liq * 20) flags.push("量/池比极高，疑似对倒");

  return [
    `📋 <b>${esc(p.baseToken?.symbol)}</b> · ${esc(chain)} · ${esc(p.dexId)} · 池龄 ${ageH}h`,
    `价 $${p.priceUsd ?? "?"} ｜ MC ${money(mc)} ｜ 池 ${money(liq)}`,
    `量 5m ${money(p.volume?.m5)} / 1h ${money(p.volume?.h1)} / 24h ${money(p.volume?.h24)}`,
    `涨跌 5m ${p.priceChange?.m5 ?? 0}% ｜ 1h ${p.priceChange?.h1 ?? 0}% ｜ 24h ${p.priceChange?.h24 ?? 0}%`,
    `笔数 5m 买${t5.buys || 0}/卖${t5.sells || 0} ｜ 1h 买${t1.buys || 0}/卖${t1.sells || 0}`,
    `社交：${socials.length ? esc(socials.join("/")) : "无"}`,
    `⚠️ 硬风险：${sec.risks.length ? esc(sec.risks.join("、")) : "未发现"}`,
    sec.notes.length ? esc(sec.notes.join(" / ")) : null,
    flags.length ? `🚩 形态告警：${esc(flags.join("；"))}` : null,
    `其他池 ${ps.length - 1} 个 ｜ 📊 ${p.url}`,
  ].filter(Boolean).join("\n");
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (req.method !== "POST" || url.pathname !== `/tg/${env.HOOK_SECRET}`)
      return new Response("ok");

    let body;
    try { body = await req.json(); } catch { return new Response("ok"); }
    const m = body.message || body.edited_message;
    if (!m?.text) return new Response("ok");

    const allow = (env.ALLOWED_CHATS || "").split(",").map(s => s.trim()).filter(Boolean);
    if (allow.length && !allow.includes(String(m.chat.id))) return new Response("ok");

    const text = m.text.trim();
    if (/^\/help/.test(text)) {
      await reply(env, m, "把 CA 直接丢进群，或 <code>/ca &lt;地址&gt;</code>，我回基础功课。\n支持 BSC / Solana / Robinhood，自动判链。");
      return new Response("ok");
    }

    const q = text.replace(/^\/ca\s*/i, "");
    const hit = (q.match(EVM) || q.match(SOL) || [])[0];
    if (!hit) return new Response("ok");
    if (/^\/(start|stat|settings)/.test(text)) return new Response("ok");

    await reply(env, m, await report(hit));
    return new Response("ok");
  }
};

async function reply(env, m, text) {
  const payload = {
    chat_id: m.chat.id, text: text.slice(0, 4000), parse_mode: "HTML",
    disable_web_page_preview: true, reply_to_message_id: m.message_id,
  };
  if (m.message_thread_id) payload.message_thread_id = m.message_thread_id;
  await fetch(`https://api.telegram.org/bot${env.TG_TOKEN}/sendMessage`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
}
