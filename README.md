# Meme 雷达

Debot（人工，管「谁在买」）+ 自建脚本（管「这币本身怎么样」）双轨方案的自建一侧。

- `scan.py` —— 每 15 分钟扫 BSC / Solana / Robinhood 新池，过初筛 + 安全检测 + 打分，达标推 TG。
- `followup.py` —— 对推送过的候选按 1/2/4/8/24h 打快照，24h 后打标签入库。
- `review.py` —— 攒够样本后统计各维度与 `alive` 的相关性，用来调阈值和权重。
- `verify_sources.py` —— 部署前预检，确认各免费源可用并解析需回填的值。
- `worker/` —— Cloudflare Worker，群里丢 CA 出报告（webhook）。

## 首次部署

```bash
pip install -r requirements.txt
python verify_sources.py     # 必须 PASS 才继续
python scan.py               # 干跑；不配 TG_TOKEN 时只打印不发送
```

## 需要人工完成的部分

- Telegram bot 建群/开话题/拿 chat_id（见方案文档 §2）
- Debot 免费档配置（见方案文档 §3）
- GitHub Secrets：`TG_TOKEN`、`TG_CHAT_ID`、`TG_THREAD_SCAN`
- `config.py` 里 `EXPLORER` 的 bsc / solana 两项（留空待填）

## 红线

本仓库不实现也不得添加：任何私钥、钱包、自动买入相关功能。
