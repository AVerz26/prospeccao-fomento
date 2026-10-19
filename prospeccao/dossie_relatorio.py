"""Seção "Dossiê de dados por área" (HTML/PDF) e abas do Excel."""
from __future__ import annotations

import datetime as dt
import html

import pandas as pd

e = html.escape
UN = {"Quantidade produzida": "t", "Área colhida": "ha", "Efetivo dos rebanhos": "cabeças"}


def _n(v) -> str:
    return "n/d" if v is None else f"{v:,.0f}".replace(",", ".")


def _pct(a, b) -> str:
    return "n/d" if not b else f"{a / b:.1%}".replace(".", ",")


def _linhas_territorio(terr: dict) -> list[dict]:
    rows = []
    for chave, d in terr.items():
        for var in sorted({l["variavel"] for l in d["serie"]}):
            serie = [l for l in d["serie"] if l["variavel"] == var]
            anos = sorted({l["ano"] for l in serie})
            v = lambda uf, ano: next((l["valor"] for l in serie if l["uf"] == uf and l["ano"] == ano), None)  # noqa: E731
            a1, a0 = anos[-1], anos[0]
            mt, br, mt0 = v("MT", a1), v("BR", a1), v("MT", a0)
            rows.append({"indicador": f"{d['nome']} — {var.lower()} ({UN.get(var, '')})", "ano": a1, "mt": mt, "br": br,
                         "part": (mt / br) if mt and br else None,
                         "var": ((mt / mt0 - 1) if mt and mt0 else None), "ano0": a0})
    return rows


def html_secao(dados: dict, cfg: dict) -> str:
    por_id = {a["id"]: a for a in cfg["areas"]}
    out = ["<h2>Dossiê de dados por área</h2>",
           "<p class=sub>Dados abertos que sustentam as 9 ideias de fomento para ICTs em Mato Grosso: território (IBGE, INPE), "
           "capacidade científica (OpenAlex, 2021–2025), financiamento multilateral (Banco Mundial, projetos no Brasil) "
           "e proposições legislativas (Câmara dos Deputados, 2023 em diante).</p>",
           "<h3>Mato Grosso no Brasil (IBGE)</h3><table><tr><th>Indicador</th><th>Ano</th><th>MT</th><th>Brasil</th>"
           "<th>Part. de MT</th><th>Var. MT no período</th></tr>"]
    for r in _linhas_territorio(dados["territorio"]):
        var = "n/d" if r["var"] is None else f"{r['var']:+.0%} desde {r['ano0']}"
        out.append(f"<tr><td>{e(r['indicador'])}</td><td>{r['ano']}</td><td>{_n(r['mt'])}</td><td>{_n(r['br'])}</td>"
                   f"<td><b>{_pct(r['mt'], r['br'])}</b></td><td>{var}</td></tr>")
    out.append("</table>")

    focos = dados.get("focos") or {}
    if focos:
        biomas = sorted({b for a in focos.values() for b in a["MT"]})
        out.append("<h3>Focos de calor (INPE, satélite de referência)</h3><table><tr><th>Ano</th><th>MT</th><th>Brasil</th>"
                   "<th>MT / Brasil</th>" + "".join(f"<th>MT {e(b)}</th>" for b in biomas) + "</tr>")
        for ano in sorted(focos):
            mt, br = sum(focos[ano]["MT"].values()), sum(focos[ano]["BR"].values())
            out.append(f"<tr><td>{ano}</td><td>{_n(mt)}</td><td>{_n(br)}</td><td>{_pct(mt, br)}</td>" +
                       "".join(f"<td>{_n(focos[ano]['MT'].get(b, 0))}</td>" for b in biomas) + "</tr>")
        out.append("</table><p class=sub>Os focos medem detecções de calor por satélite, não área queimada, e variam muito com o clima de cada ano.</p>")

    for aid, d in dados["areas"].items():
        a = por_id[aid]
        c, f, l = d["capacidade"], d["financiamento"], d["legislacao"]
        out.append(f"<div class=card><h3>{e(a['nome'])}</h3><ul>")
        out.append(f"<li><b>Produção científica {c['anos']}:</b> mundo {_n(c['mundo_total'])} · Brasil {_n(c['brasil_total'])} · "
                   f"ICTs de MT acompanhadas {_n(c['mt_total'])} ({_pct(c['mt_total'], c['brasil_total'])} do Brasil)</li>")
        if c["icts_mt"]:
            out.append("<li><b>Por ICT de MT:</b> " + " · ".join(f"{e(k)} {v}" for k, v in c["icts_mt"].items()) + "</li>")
        terr = [dados["territorio"][t] for t in a["territorio"] if t in dados["territorio"]]
        for t in terr:
            lin = [x for x in _linhas_territorio({"x": t}) if "produzida" in x["indicador"] or "rebanho" in x["indicador"].lower() or "Efetivo" in x["indicador"]]
            if lin:
                x = lin[0]
                out.append(f"<li><b>Peso de MT em {e(t['nome'])}:</b> {_pct(x['mt'], x['br'])} do Brasil ({x['ano']})</li>")
        out.append("</ul>")
        fora = [t for t in c["top_br"] if t["uf"] != "Mato Grosso"][:6]
        if fora:
            out.append("<b>Principais ICTs do Brasil na área</b> <small>(parceiros potenciais para expansão)</small><ul>" +
                       "".join(f"<li>{e(t['nome'])} <small>· {e(t['uf'] or 'n/d')} · {t['obras']} trabalhos</small></li>" for t in fora) + "</ul>")
        if f["projetos"]:
            tot = f" · US$ {f['total_usd'] / 1e6:,.0f} mi".replace(",", ".") if f["total_usd"] else ""
            out.append(f"<b>Banco Mundial no Brasil</b> <small>({f['n']} projetos desde 2015{tot})</small><ul>" +
                       "".join(f"<li><a href='{e(p['url'])}'>{e((p['nome'] or '')[:110])}</a> <small>· {p['aprovado']}{' (prevista)' if p['aprovado'] > dt.date.today().isoformat() else ''}"
                               f"{' · US$ ' + format(p['valor_usd'] / 1e6, ',.0f').replace(',', '.') + ' mi' if p['valor_usd'] else ''}</small></li>"
                               for p in f["projetos"][:4]) + "</ul>")
        if l["proposicoes"]:
            out.append(f"<b>Proposições na Câmara</b> <small>({l['n']} desde 2023 com termos da área na ementa)</small><ul>" +
                       "".join(f"<li><a href='{e(p['url'])}'>{e(p['tipo'])}</a> <small>· {e(p['ementa'][:130])}</small></li>"
                               for p in l["proposicoes"][:3]) + "</ul>")
        out.append("</div>")
    out.append("<h3>Limites do dossiê</h3><ul><li>A contagem de trabalhos usa título e resumo em inglês no OpenAlex; "
               "a afiliação conta uma obra para cada instituição de MT que aparece nela.</li>"
               "<li>Projetos do Banco Mundial são filtrados por termos no nome e no resumo: podem trazer projetos apenas tangentes.</li>"
               "<li>A busca nas proposições é por termo na ementa; propostas sobre o tema com outro vocabulário não aparecem.</li>"
               "<li>Não estão incluídos editais abertos de FAPEMAT, CNPq ou FINEP, que precisam de coleta própria.</li></ul>")
    return "\n".join(out)


def abas_excel(dados: dict, cfg: dict) -> dict[str, pd.DataFrame]:
    por_id = {a["id"]: a["nome"] for a in cfg["areas"]}
    terr = pd.DataFrame([{"Indicador": r["indicador"], "Ano": r["ano"], "MT": r["mt"], "Brasil": r["br"],
                          "Participação MT": r["part"], f"Variação MT desde": r["var"], "Ano base": r["ano0"]}
                         for r in _linhas_territorio(dados["territorio"])])
    focos = pd.DataFrame([{"Ano": int(a), "Recorte": rec, "Bioma": b, "Focos": n}
                          for a, d in (dados.get("focos") or {}).items() for rec in ("MT", "BR") for b, n in d[rec].items()])
    icts, top, wb, cam = [], [], [], []
    for aid, d in dados["areas"].items():
        nome = por_id[aid]
        icts += [{"Área": nome, "ICT de MT": k, "Trabalhos (5 anos)": v} for k, v in d["capacidade"]["icts_mt"].items()]
        top += [{"Área": nome, "ICT do Brasil": t["nome"], "UF": t["uf"], "Trabalhos (5 anos)": t["obras"]} for t in d["capacidade"]["top_br"]]
        wb += [{"Área": nome, "Projeto": p["nome"], "Aprovado": p["aprovado"], "Valor (US$)": p["valor_usd"], "Status": p["status"], "URL": p["url"]}
               for p in d["financiamento"]["projetos"]]
        cam += [{"Área": nome, "Proposição": p["tipo"], "Ementa": p["ementa"], "URL": p["url"]} for p in d["legislacao"]["proposicoes"]]
    return {"Dossiê Território IBGE": terr, "Dossiê Focos INPE": focos, "Dossiê ICTs de MT": pd.DataFrame(icts),
            "Dossiê ICTs do Brasil": pd.DataFrame(top), "Dossiê Banco Mundial": pd.DataFrame(wb), "Dossiê Câmara": pd.DataFrame(cam)}
