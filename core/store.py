import json, os, time, pathlib

STATE = pathlib.Path("state")
DATA = pathlib.Path("data")
STATE.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)

SEEN = STATE / "seen.json"
TRACK = STATE / "track.json"
CAND = DATA / "candidates.jsonl"
OUT = DATA / "outcomes.jsonl"


def _load(p, default):
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text())
    except Exception:
        return default


def _save(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False))


def load_seen(ttl_hours: int) -> dict:
    seen = _load(SEEN, {})
    cut = time.time() - ttl_hours * 3600
    return {k: v for k, v in seen.items() if v > cut}


def save_seen(seen: dict):
    _save(SEEN, seen)


def load_track() -> dict:
    return _load(TRACK, {})


def save_track(t: dict, cap: int):
    if len(t) > cap:
        t = dict(sorted(t.items(), key=lambda kv: kv[1]["t0"])[-cap:])
    _save(TRACK, t)


def append(path, obj):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")


def read_jsonl(path):
    if not pathlib.Path(path).exists():
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    return rows
