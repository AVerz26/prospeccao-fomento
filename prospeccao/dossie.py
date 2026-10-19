"""Dossiê de dados por área: território (IBGE, INPE), capacidade científica das ICTs (OpenAlex),
financiamento multilateral (Banco Mundial) e proposições legislativas (Câmara dos Deputados)."""
from __future__ import annotations

import datetime as dt
import io
import json
import logging
import unicodedata

import pandas as pd

from . import ciencia as _oa
from .editais import relevante
from .util import CACHE_DIR, Http, or_query

log = logging.getLogger(__name__)

SIDRA = "https://apisidra.ibge.gov.br/values"
INPE_REF = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/anual/Brasil_sat_ref/focos_br_ref_{ano}.zip"
WB = "https://search.worldbank.org/api/v3/projects"
CAMARA = "https://dadosabertos.camara.leg.br/api/v2/proposicoes"
CULTURAS = {"soja": "Soja (em grão)", "milho": "Milho (em grão)", "algodao": "Algodão herbáceo (em caroço)"}


# ------------------------------------------------------------------ IBGE
def _sidra(http: Http, caminho: str) -> list[dict]:
    r = http.get_json(f"{SIDRA}/{caminho}", min_interval=0.5)
    if not isinstance(r, list) or len(r) < 2:
        return []
    cab, linhas = r[0], r[1:]
    dims = {k: v for k, v in cab.items() if k.startswith("D") and k.endswith("N")}
    achar = lambda *ps: next((k for k, v in dims.items() if any(p in v.lower() for p in ps)), None)  # noqa: E731
    k_var, k_ano = achar("variável"), achar("ano")
    k_prod = achar("produto", "lavoura")
    k_terr = next((k for k in dims if k not in (k_var, k_ano, k_prod) and
                   {l[k] for l in linhas} <= {"Brasil", "Mato Grosso"}), None)
    out = []
    for l in linhas:
        try:
            out.append({"uf": "MT" if l[k_terr] == "Mato Grosso" else "BR", "variavel": l[k_var], "ano": int(l[k_ano]),
                        "produto": l[k_prod] if k_prod else None, "unidade": l["MN"], "valor": float(l["V"])})
        except (TypeError, ValueError, KeyError):
            continue
    return out


def territorio_ibge(http: Http) -> dict:
    res: dict = {}
    lav = _sidra(http, "t/5457/n1/1/n3/51/v/214,216/p/last%205/c782/all")
    for chave, prefixo in CULTURAS.items():
        linhas = [l for l in lav if l["produto"] == prefixo]
        if linhas:
            res[chave] = {"nome": linhas[0]["produto"], "serie": linhas}
    reb = _sidra(http, "t/3939/n1/1/n3/51/v/105/p/last%205/c79/2670")
    if reb:
        res["rebanho"] = {"nome": "Rebanho bovino", "serie": reb}
    return res


# ------------------------------------------------------------------ INPE
def focos_inpe(http: Http, anos: range) -> dict:
    """Focos de calor (satélite de referência) por ano, bioma e UF (MT vs Brasil). Anos fechados ficam em cache."""
    cf = CACHE_DIR / "inpe_focos.json"
    cache = json.loads(cf.read_text(encoding="utf-8")) if cf.exists() else {}
    for ano in anos:
        if str(ano) in cache:
            continue
        try:
            r = http.s.get(INPE_REF.format(ano=ano), timeout=180)
            r.raise_for_status()
            df = pd.read_csv(io.BytesIO(r.content), compression="zip", usecols=lambda c: c.lower() in ("estado", "bioma"))
        except Exception as e:  # download pesado/instável: segue com o que houver
            log.warning("INPE %s indisponível: %s", ano, str(e)[:100])
            continue
        df.columns = [c.lower() for c in df.columns]
        mt = df[df["estado"].str.upper() == "MATO GROSSO"]
        cache[str(ano)] = {"BR": df["bioma"].value_counts().to_dict(), "MT": mt["bioma"].value_counts().to_dict()}
        cf.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        log.info("INPE    focos %d: Brasil %d | MT %d", ano, len(df), len(mt))
    return {a: v for a, v in cache.items() if int(a) in anos}


# ------------------------------------------------------------------ OpenAlex: capacidade das ICTs
def _oa_get(http: Http, filt: str, **extra):
    params = {"filter": filt, **extra}
    if "group_by" not in extra:          # group_by não aceita select/per-page
        params.update({"per-page": 1, "select": "id"})
    return http.get_json(_oa.BASE, params=_oa._p(params), min_interval=0.3)


def capacidade(http: Http, area: dict, icts: list[dict]) -> dict:
    y1 = dt.date.today().year - 1
    anos = f"{y1 - 4}-{y1}"
    q = or_query(area["kw"], 6) + (f" AND ({' OR '.join(area['ctx'])})" if area.get("ctx") else "")
    base = f"title_and_abstract.search:{q},publication_year:{anos}"
    mundo = _oa_get(http, base, group_by="publication_year") or {}
    br = _oa_get(http, f"{base},authorships.institutions.country_code:BR", group_by="publication_year") or {}
    serie = lambda r: {int(g["key"]): g["count"] for g in r.get("group_by", [])}  # noqa: E731
    ids = "|".join(i["id"] for i in icts)
    mt = _oa_get(http, f"{base},authorships.institutions.id:{ids}", group_by="authorships.institutions.id") or {}
    por_ict = {g["key"].split("/")[-1]: g["count"] for g in mt.get("group_by", [])}
    # principais instituições do Brasil (dentre as 30 mais frequentes, só as de país BR)
    topo = _oa_get(http, f"{base},authorships.institutions.country_code:BR", group_by="authorships.institutions.id") or {}
    chaves = [g["key"].split("/")[-1] for g in topo.get("group_by", [])][:30]
    contagem = {g["key"].split("/")[-1]: g["count"] for g in topo.get("group_by", [])}
    nomes = {}
    if chaves:
        inst = http.get_json("https://api.openalex.org/institutions", params=_oa._p({
            "filter": "openalex:" + "|".join(chaves), "per-page": 30, "select": "id,display_name,country_code,geo"}),
            min_interval=0.3) or {}
        nomes = {i["id"].split("/")[-1]: i for i in inst.get("results", []) if i.get("country_code") == "BR"}
    top_br = [{"id": k, "nome": nomes[k]["display_name"], "uf": (nomes[k].get("geo") or {}).get("region"), "obras": contagem[k]}
              for k in chaves if k in nomes][:8]
    sm, sb = serie(mundo), serie(br)
    return {"anos": anos, "mundo": sm, "brasil": sb, "mundo_total": sum(sm.values()), "brasil_total": sum(sb.values()),
            "mt_total": (mt.get("meta") or {}).get("count", 0),
            "icts_mt": {i["nome"]: por_ict.get(i["id"], 0) for i in icts}, "top_br": top_br}


# ------------------------------------------------------------------ Banco Mundial
def financiamento(http: Http, area: dict) -> dict:
    achados: dict[str, dict] = {}
    for termo in area["wb"]:
        r = http.get_json(WB, params={"format": "json", "qterm": termo, "countrycode_exact": "BR", "rows": 40,
                                      "fl": "id,project_name,boardapprovaldate,totalamt,project_abstract,status",
                                      "srt": "boardapprovaldate", "order": "desc"}, min_interval=0.5) or {}
        for pid, p in (r.get("projects") or {}).items():
            texto = f"{p.get('project_name', '')} {(p.get('project_abstract') or '')[:350]}"   # só o início do resumo: evita projetos tangentes
            if relevante(texto, [termo]) and (p.get("boardapprovaldate") or "") >= "2015":
                achados.setdefault(pid, p)
    def valor(p):
        try:
            return float(str(p.get("totalamt", "0")).replace(",", ""))
        except ValueError:
            return 0.0
    lista = sorted(achados.values(), key=lambda p: p.get("boardapprovaldate") or "", reverse=True)
    return {"n": len(lista), "total_usd": sum(valor(p) for p in lista),
            "projetos": [{"id": p["id"], "nome": p.get("project_name"), "aprovado": (p.get("boardapprovaldate") or "")[:10],
                          "valor_usd": valor(p), "status": p.get("status"),
                          "url": f"https://projects.worldbank.org/en/projects-operations/project-detail/{p['id']}"}
                         for p in lista[:6]]}


# ------------------------------------------------------------------ Câmara dos Deputados
def proposicoes(http: Http, desde: str = "2023-01-01") -> list[dict]:
    """Todas as PL/PLP/PEC/MPV/PDL apresentadas desde a data (paginado). A busca por palavra-chave da API só
    olha as palavras de indexação, então o filtro por tema é feito localmente na ementa."""
    url, params, out = CAMARA, {"siglaTipo": "PL,PLP,PEC,MPV,PDL", "dataInicio": desde, "itens": 100,
                                "ordem": "DESC", "ordenarPor": "id"}, []
    while url and len(out) < 30000:
        r = http.get_json(url, params=params, headers={"Accept": "application/json"}, min_interval=0.3)
        if not r:
            break
        out += r.get("dados", [])
        url, params = next((l["href"] for l in r.get("links", []) if l["rel"] == "next"), None), None
    log.info("Câmara  %d proposições desde %s", len(out), desde)
    return out


def _norm(t: str) -> str:
    return unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()


def legislacao(area: dict, props: list[dict]) -> dict:
    termos = [_norm(t) for t in area["pt"]]
    achadas = [p for p in props if any(t in _norm(p.get("ementa")) for t in termos)]
    return {"n": len(achadas), "proposicoes": [{"id": p["id"], "tipo": f"{p['siglaTipo']} {p['numero']}/{p['ano']}",
                                                "ementa": (p.get("ementa") or "")[:220],
                                                "url": f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={p['id']}"}
                                               for p in achadas[:6]]}


# ------------------------------------------------------------------ orquestração
def coletar(http: Http, cfg: dict) -> dict:
    hoje = dt.date.today()
    log.info("Dossiê: território (IBGE, INPE)")
    out = {"territorio": territorio_ibge(http), "focos": focos_inpe(http, range(hoje.year - 7, hoje.year)), "areas": {}}
    props = proposicoes(http)
    for a in cfg["areas"]:
        out["areas"][a["id"]] = {"capacidade": capacidade(http, a, cfg["icts_mt"]), "financiamento": financiamento(http, a),
                                 "legislacao": legislacao(a, props)}
        c, f, l = out["areas"][a["id"]]["capacidade"], out["areas"][a["id"]]["financiamento"], out["areas"][a["id"]]["legislacao"]
        log.info("Dossiê  %-24s obras 5a: mundo %6d | BR %5d | MT %4d | Banco Mundial %2d proj | Câmara %2d proposições",
                 a["id"], c["mundo_total"], c["brasil_total"], c["mt_total"], f["n"], l["n"])
    return out
