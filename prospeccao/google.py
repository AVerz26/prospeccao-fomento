"""Google News (RSS, sem chave) e Google Trends (pytrends, não oficial).

Não fazemos scraping da busca do Google (viola os termos e é bloqueada); usamos só RSS e Trends.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from urllib.parse import quote
from statistics import mean

from .util import CACHE_DIR, Http, or_query

log = logging.getLogger(__name__)
NEWS = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def _news(http: Http, q: str) -> list[dict]:
    xml = http.request("GET", NEWS.format(q=quote(q)), min_interval=1.5)
    if not xml:
        return []
    try:
        root = ET.fromstring(xml.encode("utf-8"))
    except ET.ParseError:
        return []
    out = []
    for it in root.iter("item"):
        g = {c.tag: (c.text or "") for c in it}
        titulo, _, dominio = g.get("title", "").rpartition(" - ")
        out.append({"titulo": titulo or g.get("title"), "url": g.get("link"), "dominio": dominio,
                    "data": g.get("pubDate")})
    return out


def noticias(http: Http, temas: list[dict], n_manchetes: int = 5) -> dict[str, dict]:
    """Mesmo formato do coletor GDELT: intensidade, tendência (30d vs 30d anteriores) e manchetes.
    O feed devolve no máximo ~100 itens por consulta: temas muito quentes saturam e a tendência tende a 0."""
    hoje = dt.date.today()
    d30, d60 = hoje - dt.timedelta(days=30), hoje - dt.timedelta(days=60)
    out: dict[str, dict] = {}
    for t in temas:
        base = or_query(t["keywords_en"], 6)
        rec = _news(http, f"{base} after:{d30} before:{hoje}")
        ant = _news(http, f"{base} after:{d60} before:{d30}")
        if not rec and not ant:
            continue
        out[t["id"]] = {"intensidade": len(rec), "tendencia": (len(rec) / len(ant) - 1) if ant else None,
                        "manchetes": rec[:n_manchetes], "fonte": "Google News"}
        log.info("GNews   %-32s %3d (30d) vs %3d (30d ant.)", t["id"], len(rec), len(ant))
    return out


def trends(http: Http, temas: list[dict], pausa: float = 15.0) -> dict[str, dict]:
    """Tendência de buscas (12 meses, mundo) + consultas relacionadas em alta para o 1º termo de cada tema."""
    try:
        from pytrends.request import TrendReq
    except ImportError:
        log.warning("pytrends não instalado — Google Trends ignorado (pip install pytrends)")
        return {}
    import warnings
    warnings.filterwarnings("ignore", category=FutureWarning)

    out: dict[str, dict] = {}
    falhas = 0
    # cache de 7 dias por termo: o Trends limita requisições (429), então execuções sucessivas completam o que faltou
    cf = CACHE_DIR / "trends.json"
    cache = json.loads(cf.read_text(encoding="utf-8")) if cf.exists() else {}
    pt = TrendReq(hl="en-US", tz=0, timeout=(10, 30))
    for t in temas:
        termo = t["keywords_en"][0]
        hit = cache.get(termo)
        if hit and time.time() - hit["ts"] < 7 * 86400:
            out[t["id"]] = hit["data"]
            continue
        try:
            pt.build_payload([termo], timeframe="today 12-m", geo="")
            serie = pt.interest_over_time()
            rel = pt.related_queries().get(termo, {})
        except Exception as e:  # pytrends levanta TooManyRequests, ResponseError, etc.
            falhas += 1
            log.warning("Trends falhou para %s: %s", t["id"], str(e)[:100])
            if falhas >= 3:
                log.warning("Google Trends instável (3 falhas seguidas) — interrompido")
                break
            time.sleep(pausa * 3)
            continue
        falhas = 0
        vals = [int(v) for v in serie[termo].tolist()][:-1] if termo in serie else []  # descarta semana parcial
        if len(vals) >= 26:
            k = len(vals) // 4
            antes, depois = mean(vals[:k]), mean(vals[-k:])
            tendencia = (depois / antes - 1) if antes else None
        else:
            tendencia = None
        toks = {w for w in re.findall(r"[a-z]+", termo.lower()) if len(w) >= 5}
        em_alta = []
        for key in ("rising", "top"):
            df = rel.get(key)
            if df is None or df.empty:
                continue
            for q, v in zip(df["query"], df["value"]):
                if any(w in q.lower() for w in toks) and q not in [x["consulta"] for x in em_alta]:
                    em_alta.append({"consulta": q, "valor": int(v), "tipo": key})
        out[t["id"]] = {"termo": termo, "tendencia": tendencia, "interesse_atual": vals[-1] if vals else None,
                        "consultas": em_alta[:8]}
        cache[termo] = {"ts": time.time(), "data": out[t["id"]]}
        cf.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        log.info("Trends  %-32s '%s' tendência %s", t["id"], termo,
                 f"{tendencia:+.0%}" if tendencia is not None else "n/d")
        time.sleep(pausa)
    return out
