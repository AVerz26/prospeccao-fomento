"""Radar de tecnologias emergentes: sinais de estágio inicial (preprints, código aberto, startups, pesquisa financiada).

Fontes verificadas: OpenAlex (preprints), arXiv, GitHub, Hugging Face, Y Combinator, AgFunder News (RSS) e
Horizon Europe (tipo de ação como proxy de TRL baixo: o TRL em si não está acessível pela API).
"""
from __future__ import annotations

import datetime as dt
import logging
import math
import os
import re
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

from . import ciencia as _oa
from .editais import horizon, relevante
from .util import Http, or_query

log = logging.getLogger(__name__)

MIN_SINAIS = 12   # mínimo de ocorrências somadas nas fontes para calcular o estágio/score
ARXIV = "https://export.arxiv.org/api/query"
GITHUB = "https://api.github.com/search/repositories"
YC = "https://api.ycombinator.com/v0.1/companies"
AGFUNDER = "https://agfundernews.com/feed"
NS = {"a": "http://www.w3.org/2005/Atom", "o": "http://a9.com/-/spec/opensearch/1.1/"}


def _janelas(hoje: dt.date):
    """Dois semestres (recente e anterior) e dois anos (recente e anterior)."""
    s = lambda d: dt.timedelta(days=d)  # noqa: E731
    return {"rec6": (hoje - s(182), hoje), "ant6": (hoje - s(364), hoje - s(183)),
            "rec12": (hoje - s(364), hoje), "ant12": (hoje - s(728), hoje - s(365))}


# ---------------------------------------------------------------- OpenAlex
def _oa_contagem(http: Http, q: str, ini, fim, tipo: str | None = None) -> int | None:
    filt = f"title_and_abstract.search:{q},from_publication_date:{ini},to_publication_date:{fim}"
    if tipo:
        filt += f",type:{tipo}"
    r = http.get_json(_oa.BASE, params=_oa._p({"filter": filt, "per-page": 1, "select": "id"}), min_interval=0.3)
    return ((r or {}).get("meta") or {}).get("count")


# ---------------------------------------------------------------- arXiv
def _arxiv(http: Http, kws: list[str], ini, fim, n: int = 1, ctx: list[str] | None = None) -> tuple[int | None, list[dict]]:
    c = f" AND ({' OR '.join(f'all:{w}' for w in ctx)})" if ctx else ""
    q = "(" + " OR ".join(f'all:"{k}"' for k in kws[:6]) + f"){c} AND submittedDate:[{ini:%Y%m%d}0000 TO {fim:%Y%m%d}2359]"
    xml = http.request("GET", ARXIV, params={"search_query": q, "start": 0, "max_results": max(n, 1),
                                             "sortBy": "submittedDate", "sortOrder": "descending"}, min_interval=3.5)
    if not xml:
        return None, []
    try:
        root = ET.fromstring(xml.encode("utf-8"))
        total = int(root.find("o:totalResults", NS).text)
    except (ET.ParseError, AttributeError, ValueError):
        return None, []
    itens = [{"titulo": " ".join((e.findtext("a:title", "", NS)).split()),
              "url": e.findtext("a:id", "", NS), "data": (e.findtext("a:published", "", NS) or "")[:10]}
             for e in root.findall("a:entry", NS)][:n]
    return total, itens


# ---------------------------------------------------------------- GitHub
def _github(http: Http, kws: list[str], ini, fim, n: int = 1) -> tuple[int | None, list[dict]]:
    q = " OR ".join(f'"{k}"' for k in kws[:4]) + f" in:name,description created:{ini}..{fim}"
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"} | ({"Authorization": f"Bearer {token}"} if token else {})
    r = http.get_json(GITHUB, params={"q": q, "sort": "stars", "order": "desc", "per_page": max(n, 1)},
                      headers=headers, min_interval=2.5 if token else 6.5)
    if not r or "total_count" not in r:
        return None, []
    itens = [{"nome": i["full_name"], "estrelas": i["stargazers_count"], "url": i["html_url"],
              "desc": (i.get("description") or "")[:140]} for i in r.get("items", [])][:n]
    return int(r["total_count"]), itens


# ---------------------------------------------------------------- Hugging Face
def _hf(http: Http, termo: str, tipo: str) -> tuple[int | None, list[dict]]:
    r = http.get_json(f"https://huggingface.co/api/{tipo}", params={"search": termo, "sort": "createdAt",
                                                                    "direction": "-1", "limit": 100}, min_interval=0.5)
    if not isinstance(r, list):
        return None, []
    corte = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=90)
    n90 = sum(1 for m in r if m.get("createdAt") and
              dt.datetime.fromisoformat(m["createdAt"].replace("Z", "+00:00")) >= corte)
    itens = [{"id": m["id"], "criado": (m.get("createdAt") or "")[:10], "url": f"https://huggingface.co/{'datasets/' if tipo == 'datasets' else ''}{m['id']}"}
             for m in r[:3]]
    return n90, itens


# ---------------------------------------------------------------- Y Combinator
def _yc(http: Http, termos: list[str], ano_corte: int) -> list[dict]:
    achadas: dict[str, dict] = {}
    for termo in termos[:2]:
        for pag in (1, 2, 3):
            r = http.get_json(YC, params={"q": termo, "page": pag}, min_interval=0.5)
            if not r:
                break
            for c in r.get("companies", []):
                m = re.search(r"(\d{2,4})", c.get("batch") or "")
                if not m:
                    continue
                ano = int(m.group(1)) if len(m.group(1)) == 4 else 2000 + int(m.group(1))
                texto = f"{c.get('oneLiner', '')} {c.get('longDescription', '')}"
                if ano >= ano_corte and relevante(texto, termos):
                    achadas.setdefault(c["slug"], {"nome": c["name"], "turma": c.get("batch"),
                                                   "desc": (c.get("oneLiner") or "")[:140], "url": c.get("url")})
            if pag >= int(r.get("totalPages", 1)):
                break
    return list(achadas.values())


# ---------------------------------------------------------------- AgFunder
def _agfunder(http: Http) -> list[dict]:
    xml = http.request("GET", AGFUNDER, min_interval=1.0)
    if not xml:
        return []
    try:
        root = ET.fromstring(xml.encode("utf-8"))
    except ET.ParseError:
        return []
    out = []
    for it in root.iter("item"):
        g = {c.tag: (c.text or "") for c in it}
        desc = re.sub(r"<[^>]+>", " ", g.get("description", ""))
        out.append({"titulo": g.get("title", ""), "url": g.get("link", ""), "texto": f"{g.get('title', '')}. {desc}"})
    return out


# ---------------------------------------------------------------- coleta
def coletar(http: Http, techs: list[dict]) -> dict[str, dict]:
    hoje = dt.date.today()
    w = _janelas(hoje)
    agf = _agfunder(http)
    out: dict[str, dict] = {}
    for t in techs:
        kw, busca = t["kw"], t.get("busca", [])
        ctx = t.get("ctx") or []
        q = or_query(kw, 6) + (f" AND ({' OR '.join(ctx)})" if ctx else "")
        d: dict = {"ex": {}}
        d["pre_rec"] = _oa_contagem(http, q, *w["rec6"], tipo="preprint")
        d["pre_ant"] = _oa_contagem(http, q, *w["ant6"], tipo="preprint")
        d["oa_total12"] = _oa_contagem(http, q, *w["rec12"])
        d["ax_rec"], d["ex"]["arxiv"] = _arxiv(http, kw, *w["rec6"], n=3, ctx=ctx)
        d["ax_ant"], _ = _arxiv(http, kw, *w["ant6"], ctx=ctx)
        if ctx:   # a busca do GitHub não aceita trava de contexto sem zerar: sinal indisponível para estas tecnologias
            d["gh_rec"], d["gh_ant"], d["ex"]["github"] = None, None, []
        else:
            d["gh_rec"], d["ex"]["github"] = _github(http, kw, *w["rec12"], n=3)
            d["gh_ant"], _ = _github(http, kw, *w["ant12"])
        hfm, d["ex"]["hf_modelos"] = _hf(http, busca[0], "models") if busca else (None, [])
        hfd, d["ex"]["hf_datasets"] = _hf(http, busca[0], "datasets") if busca else (None, [])
        d["hf"] = None if hfm is None and hfd is None else (hfm or 0) + (hfd or 0)
        yc = _yc(http, busca, hoje.year - 2) if busca else []
        d["yc"], d["ex"]["yc"] = len(yc), yc[:4]
        mencoes = [a for a in agf if relevante(a["texto"], kw + busca)]
        d["agf"], d["ex"]["agfunder"] = len(mencoes), [{"titulo": a["titulo"], "url": a["url"]} for a in mencoes[:3]]
        calls: dict[str, dict] = {}
        for termo in kw[:3]:
            for c in horizon(http, termo, kw):
                calls.setdefault(c["id"], c)
        precoce = [c for c in calls.values() if re.search(r"Research and Innovation|EIC|Pathfinder", c.get("tipo") or "")]
        d["hz_total"], d["hz_precoce"] = len(calls), len(precoce)
        d["ex"]["horizon"] = sorted(precoce, key=lambda c: c["prazo"] or "9")[:3]
        out[t["id"]] = d
        log.info("Radar   %-22s preprints %s/%s | arXiv %s/%s | GitHub %s/%s | HF %s | YC %d | AgF %d | Horizon RIA %d",
                 t["id"], d["pre_rec"], d["pre_ant"], d["ax_rec"], d["ax_ant"], d["gh_rec"], d["gh_ant"], d["hf"],
                 d["yc"], d["agf"], d["hz_precoce"])
    return out


# ---------------------------------------------------------------- score
def _cresc(rec, ant):
    if rec is None or ant is None:
        return np.nan
    return (rec + 2) / (ant + 2) - 1          # suavizado: evita explosão com contagens pequenas


def calcular(techs: list[dict], pesos: dict, dados: dict[str, dict]) -> pd.DataFrame:
    rows = []
    for t in techs:
        d = dados.get(t["id"])
        if d is None:
            continue
        rows.append({"id": t["id"], "tecnologia": t["nome"], **{k: v for k, v in d.items() if k != "ex"},
                     "g_pre": _cresc(d["pre_rec"], d["pre_ant"]), "g_ax": _cresc(d["ax_rec"], d["ax_ant"]),
                     "g_gh": _cresc(d["gh_rec"], d["gh_ant"]), "mt_fit": t["mt_fit"]})
    df = pd.DataFrame(rows).set_index("id").astype({"mt_fit": float})
    pct = lambda s: s.astype(float).rank(pct=True) * 100  # noqa: E731
    lg = lambda s: s.astype(float).map(lambda v: math.log1p(v) if pd.notna(v) else np.nan)  # noqa: E731
    p = pd.DataFrame(index=df.index)
    p["cresc_pesquisa"] = pd.concat([pct(df.g_pre), pct(df.g_ax)], axis=1).mean(axis=1)
    p["atividade_pesquisa"] = pct(lg(df.pre_rec.fillna(0) + df.ax_rec.fillna(0)))
    p["codigo"] = pd.concat([pct(df.g_gh), pct(lg(df.gh_rec)), pct(lg(df.hf))], axis=1).mean(axis=1)
    p["startups"] = pd.concat([pct(lg(df.yc)), pct(lg(df.agf))], axis=1).mean(axis=1)
    p["financiamento_inicial"] = pct(lg(df.hz_precoce))
    vol = pct(lg(df.oa_total12))
    p["imaturidade"] = 100 - vol
    p["mt_fit"] = (df.mt_fit - 1) / 4 * 100
    w = pd.Series(pesos)
    ok = p[w.index].notna()
    df["score"] = (p[w.index].fillna(0).mul(w, axis=1).sum(axis=1) / ok.mul(w, axis=1).sum(axis=1)).round(1)
    for c in p.columns:
        df[f"p_{c}"] = p[c].round(0)

    def estagio(i):
        c, v = p.at[i, "cresc_pesquisa"], vol[i]
        if pd.isna(c) or pd.isna(v):
            return "n/d"
        if c >= 60 and v <= 50:
            return "Nascente"
        if c >= 60:
            return "Em aceleração"
        return "Incipiente" if v <= 35 else "Estabelecida"
    df["estagio"] = [estagio(i) for i in df.index]
    # sinais somados: abaixo disso as contagens são ruído (0 vs 0 não é "nascente", é falta de dado)
    cols = ["pre_rec", "pre_ant", "ax_rec", "ax_ant", "gh_rec", "gh_ant", "hf", "yc", "agf", "hz_total"]
    insuf = df[cols].fillna(0).sum(axis=1) < MIN_SINAIS
    df.loc[insuf, "estagio"] = "Dados insuficientes"
    df.loc[insuf, "score"] = np.nan
    return df.sort_values("score", ascending=False)
