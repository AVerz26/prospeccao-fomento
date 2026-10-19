"""GDELT: intensidade e tendência de cobertura na mídia global + manchetes recentes."""
from __future__ import annotations

import logging
from statistics import mean

from .util import Http, or_query

log = logging.getLogger(__name__)
API = "https://api.gdeltproject.org/api/v2/doc/doc"
GAP = 10.0  # GDELT limita ~1 requisição a cada 5 s; 429 em rajada exige folga


def coletar(http: Http, temas: list[dict], timespan: str = "6months", n_manchetes: int = 5) -> dict[str, dict]:
    out: dict[str, dict] = {}
    falhas = 0
    for t in temas:
        q = f"{or_query(t['keywords_en'], 5)} sourcelang:english"
        r = http.get_json(API, params={"query": q, "mode": "timelinevol", "format": "json",
                                       "timespan": timespan}, min_interval=GAP)
        vals = []
        try:
            vals = [p["value"] for p in r["timeline"][0]["data"]]
        except (TypeError, KeyError, IndexError):
            pass
        if len(vals) < 20:
            falhas += 1
            log.warning("GDELT sem série para %s", t["id"])
            if falhas >= 3:
                log.warning("GDELT instável (3 falhas seguidas) — mídia ignorada nesta execução")
                break
            continue
        falhas = 0
        k = max(7, len(vals) // 6)
        antes, depois = mean(vals[:k]), mean(vals[-k:])
        a = http.get_json(API, params={"query": q, "mode": "artlist", "format": "json", "sort": "hybridrel",
                                       "maxrecords": n_manchetes, "timespan": "1month"}, min_interval=GAP)
        manchetes = [{"titulo": x.get("title"), "url": x.get("url"), "dominio": x.get("domain"),
                      "data": x.get("seendate")} for x in (a or {}).get("articles", [])]
        out[t["id"]] = {"intensidade": mean(vals), "tendencia": (depois / antes - 1) if antes else None,
                        "manchetes": manchetes}
        log.info("GDELT   %-32s intens. %.5f  tendência %s", t["id"], out[t["id"]]["intensidade"],
                 f"{out[t['id']]['tendencia']:+.0%}" if out[t["id"]]["tendencia"] is not None else "n/d")
    return out
