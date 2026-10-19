"""OpenAlex: volume e crescimento de publicações por tema, incluindo anais de congressos."""
from __future__ import annotations

import datetime as dt
import logging
import os

from .util import Http, or_query

log = logging.getLogger(__name__)
BASE = "https://api.openalex.org/works"


def _p(extra: dict) -> dict:
    p = dict(extra)
    if os.getenv("OPENALEX_API_KEY"):
        p["api_key"] = os.getenv("OPENALEX_API_KEY")
    if os.getenv("OPENALEX_MAILTO"):
        p["mailto"] = os.getenv("OPENALEX_MAILTO")
    return p


def _by_year(http: Http, filt: str) -> dict[int, int]:
    r = http.get_json(BASE, params=_p({"filter": filt, "group_by": "publication_year"}), min_interval=0.3)
    if not r:
        return {}
    return {int(g["key"]): g["count"] for g in r.get("group_by", [])}


def coletar(http: Http, temas: list[dict]) -> dict[str, dict]:
    hoje = dt.date.today()
    y1 = hoje.year - 1          # último ano completo
    y0 = y1 - 2                 # base de comparação
    anos = f"{y0}-{y1}"
    conf = "primary_location.source.type:conference"

    base = _by_year(http, f"publication_year:{anos}")
    base_conf = _by_year(http, f"publication_year:{anos},{conf}")
    if not base:
        log.warning("OpenAlex indisponível (limite diário sem chave?). Defina OPENALEX_API_KEY.")
        return {}

    out: dict[str, dict] = {}
    for t in temas:
        q = or_query(t["keywords_en"], 10)
        filt = f"title_and_abstract.search:{q}"
        c = _by_year(http, f"{filt},publication_year:{anos}")
        cc = _by_year(http, f"{filt},publication_year:{anos},{conf}")
        if not c:
            continue

        def rel(series: dict, bs: dict) -> float | None:
            a, b = series.get(y0, 0), series.get(y1, 0)
            ba, bb = bs.get(y0, 0), bs.get(y1, 0)
            if min(a, ba, bb) == 0:
                return None
            return (b / bb) / (a / ba) - 1

        top = http.get_json(BASE, params=_p({
            "filter": f"{filt},publication_year:{y1}-{hoje.year}",
            "sort": "cited_by_count:desc", "per-page": 5,
            "select": "title,publication_year,cited_by_count,doi,primary_location"}), min_interval=0.3) or {}
        works = []
        for w in top.get("results", []):
            src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name")
            works.append({"titulo": w.get("title"), "ano": w.get("publication_year"),
                          "citacoes": w.get("cited_by_count"), "doi": w.get("doi"), "veiculo": src})

        out[t["id"]] = {
            "ano_ref": y1, "serie": c, "serie_conf": cc,
            "sci_volume": c.get(y1, 0), "sci_growth": rel(c, base),
            "conf_volume": cc.get(y1, 0), "conf_growth": rel(cc, base_conf),
            "top_works": works,
        }
        log.info("OpenAlex %-32s %6d pubs em %d (cresc. relativo %s)", t["id"], c.get(y1, 0), y1,
                 f"{out[t['id']]['sci_growth']:+.0%}" if out[t["id"]]["sci_growth"] is not None else "n/d")
    return out
