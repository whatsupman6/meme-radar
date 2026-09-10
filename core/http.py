import time, threading
from urllib.parse import urlparse
import requests
from config import MIN_INTERVAL

_UA = {"User-Agent": "meme-radar/1.0 (+github actions)"}
_lock = threading.Lock()
_last = {}
_session = requests.Session()
_session.headers.update(_UA)


def _throttle(url: str):
    host = urlparse(url).netloc
    gap = MIN_INTERVAL.get(host, 0.5)
    with _lock:
        prev = _last.get(host, 0.0)
        wait = gap - (time.time() - prev)
        if wait > 0:
            time.sleep(wait)
        _last[host] = time.time()


def get_json(url: str, params: dict | None = None, tries: int = 3):
    """带节流 + 指数退避的 GET。失败返回 None，绝不抛异常打断整轮扫描。"""
    for i in range(tries):
        _throttle(url)
        try:
            r = _session.get(url, params=params, timeout=20)
            if r.status_code == 429:
                time.sleep(5 * (i + 1))
                continue
            if r.status_code in (401, 403):
                # honeypot.is 文档预告过未来会要 key，这里静默降级而非崩掉
                print(f"[warn] {url} -> {r.status_code}，该源已降级跳过")
                return None
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if i == tries - 1:
                print(f"[warn] get_json failed {url}: {e}")
                return None
            time.sleep(1.5 * (i + 1))
    return None
