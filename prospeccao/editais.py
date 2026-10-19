"""Chamadas internacionais abertas: Horizon Europe (EU Funding & Tenders) e Grants.gov (EUA)."""
from __future__ import annotations

import datetime as dt
import json
import logging
import re

from .util import Http

log = logging.getLogger(__name__)

SEDIA = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
SEDIA_QUERY = {"bool": {"must": [{"terms": {"type": ["1", "2", "8"]}},
                                 {"terms": {"status": ["31094501", "31094502"]}}]}}  # previstas + abertas
TOPIC_URL = "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{}"
GRANTS = "https://api.grants.gov/v1/api/search2"


_STOP = {"and", "for", "the", "with", "from", "into", "of", "in", "on"}


def _tokens(txt: str) -> set[str]:
    return {w[:6] for w in re.findall(r"[a-z0-9]+", txt.lower()) if len(w) >= 3 and w not in _STOP}


def relevante(texto: str, keywords: list[str]) -> bool:
    """A busca das APIs é frouxa (OR entre termos): exige que todos os termos de ao menos uma palavra-chave apareçam."""
    toks = _tokens(texto)
    return any(_tokens(k) <= toks for k in keywords)


def _first(md: dict, key: str):
    v = md.get(key)
    return v[0] if isinstance(v, list) and v else v


def _parse_d(s: str | None) -> dt.date | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%m/%d/%Y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def horizon(http: Http, termo: str, keywords: list[str]) -> list[dict]:
    r = http.post_json(SEDIA, params={"apiKey": "SEDIA", "text": termo, "pageSize": 50, "pageNumber": 1},
                       multipart={"query": json.dumps(SEDIA_QUERY), "languages": '["en"]'}, min_interval=0.5)
    hoje, out = dt.date.today(), []
    for res in (r or {}).get("results", []):
        md = res.get("metadata", {})
        ident = _first(md, "identifier")
        prazo = _parse_d(_first(md, "deadlineDate"))
        if not ident or (prazo and prazo < hoje):
            continue
        if not relevante(f"{_first(md, 'title') or ''} {md.get('keywords') or ''}", keywords):
            continue
        out.append({"fonte": "Horizon Europe", "id": ident, "titulo": _first(md, "title") or res.get("summary"),
                    "prazo": prazo.isoformat() if prazo else None, "tipo": _first(md, "typesOfAction"),
                    "url": TOPIC_URL.format(ident)})
    return out


def grants_gov(http: Http, termo: str, keywords: list[str]) -> tuple[int, list[dict]]:
    r = http.post_json(GRANTS, json_body={"keyword": termo, "rows": 25, "oppStatuses": "forecasted|posted"},
                       min_interval=0.5)
    data = (r or {}).get("data") or {}
    hoje, out = dt.date.today(), []
    for h in data.get("oppHits", []):
        prazo = _parse_d(h.get("closeDate"))
        if (prazo and prazo < hoje) or not relevante(h.get("title") or "", keywords):
            continue
        out.append({"fonte": "Grants.gov (EUA)", "id": h.get("number"), "titulo": h.get("title"),
                    "prazo": prazo.isoformat() if prazo else None, "tipo": h.get("agency"),
                    "url": f"https://www.grants.gov/search-results-detail/{h.get('id')}"})
    return int(data.get("hitCount", 0)), out


def coletar(http: Http, temas: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for t in temas:
        calls: dict[str, dict] = {}
        gg_hits = 0
        kws = t["keywords_en"]
        for kw in kws[:6]:
            for c in horizon(http, kw, kws):
                calls.setdefault(c["id"], c)
            n, lst = grants_gov(http, kw, kws)
            gg_hits += n
            for c in lst:
                calls.setdefault(c["id"], c)
        lst = sorted(calls.values(), key=lambda c: (c["prazo"] is None, c["prazo"] or ""))
        out[t["id"]] = {"n": len(lst), "n_horizon": sum(c["fonte"] == "Horizon Europe" for c in lst),
                        "n_grants": sum(c["fonte"].startswith("Grants") for c in lst),
                        "grants_hits_total": gg_hits, "chamadas": lst}
        log.info("Editais %-32s %3d abertas/previstas (Horizon %d, Grants.gov %d)", t["id"], len(lst),
                 out[t["id"]]["n_horizon"], out[t["id"]]["n_grants"])
    return out
