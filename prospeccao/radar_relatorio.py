"""Seção do radar de tecnologias emergentes (HTML/PDF e planilha)."""
from __future__ import annotations

import html

import pandas as pd

e = html.escape
COR = {"Nascente": "#1a7f37", "Em aceleração": "#0969da", "Incipiente": "#8250df", "Estabelecida": "#59636e", "n/d": "#59636e"}


def _n(v) -> str:
    return "n/d" if v is None or pd.isna(v) else f"{int(v):,}".replace(",", ".")


def _var(rec, ant) -> str:
    if rec is None or ant is None or pd.isna(rec) or pd.isna(ant):
        return "n/d"
    return f"{int(rec)} ← {int(ant)}"


def _lista(titulo: str, itens: list[tuple[str, str, str]]) -> str:
    if not itens:
        return ""
    lis = "".join(f"<li><a href='{e(u)}'>{e(t[:150])}</a> <small>· {e(m)}</small></li>" for t, u, m in itens if u)
    return f"<b>{e(titulo)}</b><ul>{lis}</ul>" if lis else ""


def html_secao(df: pd.DataFrame, techs: list[dict], dados: dict[str, dict], top_cards: int = 10) -> str:
    by_id = {t["id"]: t for t in techs}
    out = ["<h2>Radar de tecnologias emergentes</h2>",
           "<p class=sub>Segunda lista, com critérios próprios: favorece tecnologias com <b>pouco volume e crescimento alto</b> "
           "(preprints, código aberto, startups e pesquisa financiada em fase inicial) — o oposto do ranking de temas acima, "
           "que premia assuntos já consolidados. Os números mostram <i>semestre recente ← semestre anterior</i> "
           "(preprints) e <i>12 meses ← 12 meses anteriores</i> (GitHub).</p>",
           "<table><tr><th>#</th><th>Tecnologia</th><th>Score</th><th>Estágio</th><th>Preprints 6m</th><th>arXiv 6m</th>"
           "<th>Repos novos 12m</th><th>HF 90d</th><th>YC</th><th>Pesquisa inicial</th></tr>"]
    for n, (tid, r) in enumerate(df.iterrows(), 1):
        out.append(f"<tr><td>{n}</td><td><a href='#r_{tid}'>{e(r['tecnologia'])}</a></td><td><b>{r['score']:.0f}</b></td>"
                   f"<td style='color:{COR.get(r['estagio'], '#000')}'><b>{e(r['estagio'])}</b></td>"
                   f"<td>{_var(r['pre_rec'], r['pre_ant'])}</td><td>{_var(r['ax_rec'], r['ax_ant'])}</td>"
                   f"<td>{_var(r['gh_rec'], r['gh_ant'])}</td><td>{_n(r['hf'])}</td><td>{_n(r['yc'])}</td>"
                   f"<td>{_n(r['hz_precoce'])}</td></tr>")
    out.append("</table>")
    for tid, r in list(df.iterrows())[:top_cards]:
        ex = dados[tid]["ex"]
        t = by_id[tid]
        out.append(f"<div class=card id=r_{tid}><h3>{e(t['nome'])} <span class=tag style='color:{COR.get(r['estagio'], '#000')}'>"
                   f"{e(r['estagio'])} · score {r['score']:.0f}</span></h3>")
        out.append(_lista("Preprints recentes (arXiv)", [(x["titulo"], x["url"], x["data"]) for x in ex.get("arxiv", [])]))
        out.append(_lista("Repositórios novos mais estrelados (GitHub, 12 meses)",
                          [(f"{x['nome']} — {x['desc']}", x["url"], f"★ {x['estrelas']}") for x in ex.get("github", [])]))
        out.append(_lista("Modelos e datasets recentes (Hugging Face)",
                          [(x["id"], x["url"], x["criado"]) for x in ex.get("hf_modelos", []) + ex.get("hf_datasets", [])]))
        out.append(_lista("Startups do Y Combinator", [(f"{x['nome']} — {x['desc']}", x["url"], x["turma"] or "")
                                                       for x in ex.get("yc", [])]))
        out.append(_lista("Em AgFunder News", [(x["titulo"], x["url"], "notícia") for x in ex.get("agfunder", [])]))
        out.append(_lista("Chamadas Horizon de pesquisa em fase inicial", [(x["titulo"] or x["id"], x["url"], f"prazo {x['prazo'] or 'n/d'}")
                                                                          for x in ex.get("horizon", [])]))
        out.append("</div>")
    out.append("<h3>Como ler o radar</h3><ul>"
               "<li><b>Estágio</b>: <i>Nascente</i> = volume baixo e crescimento alto; <i>Em aceleração</i> = crescimento alto e volume já relevante; "
               "<i>Incipiente</i> = volume baixo sem tração ainda; <i>Estabelecida</i> = volume alto, crescimento moderado.</li>"
               "<li>Contagens pequenas oscilam muito: use o crescimento como indício e leia os exemplos antes de decidir.</li>"
               "<li>O TRL das chamadas Horizon não está disponível pela API; \"pesquisa inicial\" conta chamadas do tipo "
               "<i>Research and Innovation Actions</i>/EIC, usadas aqui como aproximação.</li>"
               "<li>As consultas são em inglês e por frase: tecnologias descritas com outro vocabulário podem ficar subestimadas.</li></ul>")
    return "\n".join(x for x in out if x)


def abas_excel(df: pd.DataFrame, techs: list[dict], dados: dict[str, dict]) -> dict[str, pd.DataFrame]:
    by_id = {t["id"]: t for t in techs}
    radar = df.reset_index()[["tecnologia", "score", "estagio", "pre_rec", "pre_ant", "ax_rec", "ax_ant", "gh_rec", "gh_ant",
                              "hf", "yc", "agf", "hz_precoce", "hz_total", "oa_total12", "mt_fit"]].rename(columns={
        "tecnologia": "Tecnologia", "score": "Score", "estagio": "Estágio", "pre_rec": "Preprints OpenAlex (6m)",
        "pre_ant": "Preprints OpenAlex (6m ant.)", "ax_rec": "arXiv (6m)", "ax_ant": "arXiv (6m ant.)",
        "gh_rec": "Repos GitHub novos (12m)", "gh_ant": "Repos GitHub (12m ant.)", "hf": "HF modelos+datasets (90d)",
        "yc": "Startups YC", "agf": "Menções AgFunder", "hz_precoce": "Horizon pesquisa inicial",
        "hz_total": "Horizon total", "oa_total12": "Publicações totais (12m)", "mt_fit": "Aderência MT"})
    linhas = []
    for tid, d in dados.items():
        for fonte, itens in d["ex"].items():
            for x in itens:
                linhas.append({"Tecnologia": by_id[tid]["nome"], "Fonte": fonte,
                               "Item": x.get("titulo") or x.get("nome") or x.get("id"), "Detalhe": x.get("desc") or x.get("data") or x.get("turma") or x.get("criado") or "",
                               "URL": x.get("url")})
    return {"Radar emergentes": radar, "Radar exemplos": pd.DataFrame(linhas)}
