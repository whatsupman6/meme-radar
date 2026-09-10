import os, time, html, requests

TOKEN = os.environ.get("TG_TOKEN", "")
CHAT = os.environ.get("TG_CHAT_ID", "")
API = f"https://api.telegram.org/bot{TOKEN}"
E = html.escape


def send(text: str, thread_id: str | None = None, tries: int = 3) -> bool:
    if not TOKEN or not CHAT:
        print("[warn] TG 未配置，改为打印\n" + text)
        return False
    payload = {"chat_id": CHAT, "text": text[:4000], "parse_mode": "HTML",
               "disable_web_page_preview": True}
    if thread_id:
        payload["message_thread_id"] = int(thread_id)
    for i in range(tries):
        try:
            r = requests.post(f"{API}/sendMessage", json=payload, timeout=25)
            if r.status_code == 429:
                time.sleep(int((r.json().get("parameters") or {}).get("retry_after", 5)) + 1)
                continue
            if r.status_code == 400 and "thread" in r.text.lower():
                payload.pop("message_thread_id", None)   # 话题不存在则退回主群
                continue
            if r.ok:
                return True
            print(f"[warn] TG {r.status_code}: {r.text[:200]}")
            return False
        except Exception as e:
            if i == tries - 1:
                print(f"[warn] TG send failed: {e}")
                return False
            time.sleep(2 * (i + 1))
    return False
