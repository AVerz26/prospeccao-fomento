"""HTTP resiliente com cache em disco, rate-limit por host e robots.txt."""
from __future__ import annotations

import hashlib
import json
import logging
import pathlib
import time
import urllib.robotparser
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / ".cache"
USER_AGENT = "Mozilla/5.0 (compatible; ProspeccaoFomentoMT/1.0; pesquisa de tendencias)"


class Http:
    def __init__(self, ttl_hours: float = 12, use_cache: bool = True):
        s = requests.Session()
        retry = Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504],
                      allowed_methods=None, respect_retry_after_header=True)
        s.mount("https://", HTTPAdapter(max_retries=retry))
        s.mount("http://", HTTPAdapter(max_retries=retry))
        s.headers["User-Agent"] = USER_AGENT
        self.s = s
        self.ttl = ttl_hours * 3600
        self.use_cache = use_cache
        self._last: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        CACHE_DIR.mkdir(exist_ok=True)

    def _throttle(self, url: str, min_interval: float) -> None:
        host = urlparse(url).netloc
        wait = self._last.get(host, 0) + min_interval - time.time()
        if wait > 0:
            time.sleep(wait)
        self._last[host] = time.time()

    def allowed(self, url: str) -> bool:
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        if base not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self.s.get(base + "/robots.txt", timeout=15)
                rp.parse(r.text.splitlines()) if r.ok else rp.parse([])
                self._robots[base] = rp
            except requests.RequestException:
                self._robots[base] = None
        rp = self._robots[base]
        return True if rp is None else rp.can_fetch(USER_AGENT, url)

    def request(self, method: str, url: str, *, params: dict | None = None,
                json_body: dict | None = None, multipart: dict[str, str] | None = None,
                min_interval: float = 0.0, timeout: int = 40) -> str | None:
        """Retorna o corpo como texto, ou None em caso de falha (nunca levanta)."""
        key = hashlib.sha1(json.dumps([method, url, params, json_body, multipart],
                                      sort_keys=True, default=str).encode()).hexdigest()
        f = CACHE_DIR / f"{key}.txt"
        if self.use_cache and f.exists() and time.time() - f.stat().st_mtime < self.ttl:
            return f.read_text(encoding="utf-8")
        self._throttle(url, min_interval)
        try:
            files = {k: (None, v, "application/json") for k, v in multipart.items()} if multipart else None
            r = self.s.request(method, url, params=params, json=json_body, files=files, timeout=timeout)
            r.raise_for_status()
        except requests.RequestException as e:
            log.warning("Falha em %s %s: %s", method, url, e)
            return None
        r.encoding = r.encoding or "utf-8"
        f.write_text(r.text, encoding="utf-8")
        return r.text

    def get_json(self, url: str, **kw):
        txt = self.request("GET", url, **kw)
        return _loads(txt)

    def post_json(self, url: str, **kw):
        txt = self.request("POST", url, **kw)
        return _loads(txt)


def _loads(txt: str | None):
    if not txt:
        return None
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        log.warning("Resposta não-JSON: %s", txt[:120].replace("\n", " "))
        return None


def or_query(keywords: list[str], limit: int = 5) -> str:
    """('"a" OR "b"') — sintaxe aceita por OpenAlex e GDELT."""
    return "(" + " OR ".join(f'"{k}"' for k in keywords[:limit]) + ")"
