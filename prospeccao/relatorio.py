"""Geração do relatório HTML e da planilha Excel."""
from __future__ import annotations

import datetime as dt
import html
import json
import pathlib

import pandas as pd

e = html.escape


def _pct(v) -> str:
    return "n/d" if v is None or pd.isna(v) else f"{v:+.0%}"


def _porque(r, ciencia, editais, midia, web, tid, trends=None) -> list[str]:
    b = []
    c = (ciencia or {}).get(tid)
    if c:
        b.append(f"{c['sci_volume']:,} publicações em {c['ano_ref']}".replace(",", ".") +
                 f"; participação na ciência global {_pct(c['sci_growth'])} em 2 anos")
        if c["conf_volume"]:
            b.append(f"{c['conf_volume']:,} trabalhos em anais de congressos".replace(",", ".") +
                     f" ({_pct(c['conf_growth'])} de crescimento relativo)")
    ed = (editais or {}).get(tid)
    if ed:
        b.append(f"{ed['n']} chamadas internacionais abertas/previstas (Horizon Europe {ed['n_horizon']}, "
                 f"Grants.gov {ed['n_grants']})")
    m = (midia or {}).get(tid)
    if m and m.get("tendencia") is not None:
        b.append(f"Mídia global ({m.get('fonte', 'GDELT')}): cobertura {_pct(m['tendencia'])} no período")
    g = (trends or {}).get(tid)
    if g and g.get("tendencia") is not None:
        b.append(f"Buscas no Google (\"{g['termo']}\"): {_pct(g['tendencia'])} em 12 meses")
    w = (web or {}).get(tid)
    if w and w["mencoes"]:
        b.append("Menções nas fontes monitoradas: " + ", ".join(f"{k} {v}" for k, v in w["mencoes"].items()))
    return b


CSS = """body{font:15px/1.5 system-ui,Segoe UI,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#1b1f24}
h1{margin-bottom:0}.sub{color:#59636e;margin-top:.2rem}table{border-collapse:collapse;width:100%;margin:1rem 0}
th,td{padding:.45rem .6rem;border-bottom:1px solid #d8dee4;text-align:left}th{background:#f6f8fa}
.bar{background:#e8f0fe;border-radius:3px;height:10px}.bar>i{display:block;height:10px;background:#1a73e8;border-radius:3px}
.card{border:1px solid #d8dee4;border-radius:8px;padding:1rem 1.2rem;margin:1.2rem 0}.card h3{margin:.1rem 0}
.tag{background:#eef6ee;color:#1a7f37;border-radius:10px;padding:.1rem .6rem;font-size:.85em}
.sug{background:#fff8e6;border-left:4px solid #bf8700;padding:.5rem .8rem;margin:.6rem 0}
small,.mut{color:#59636e}a{color:#0969da}ul{margin:.3rem 0}
@page{size:A4;margin:14mm}
@media print{body{max-width:none;margin:0;font-size:11.5px;-webkit-print-color-adjust:exact;print-color-adjust:exact}
h1{font-size:22px}h2{font-size:17px;break-after:avoid}h3{break-after:avoid}
.card,tr,li{break-inside:avoid}.card{margin:.8rem 0;padding:.7rem 1rem}
th,td{padding:.2rem .4rem}td:nth-child(4){width:70px!important}td:nth-child(2){width:46%}h1{margin-top:0}.sub{font-size:11px}}"""


def html_report(df, temas, ciencia, editais, midia, web, status_web, path: pathlib.Path, trends=None) -> None:
    by_id = {t["id"]: t for t in temas}
    hoje = dt.date.today().strftime("%d/%m/%Y")
    out = [f"<!doctype html><meta charset=utf-8><title>Prospecção de tendências – MT</title><style>{CSS}</style>",
           "<h1>Prospecção de tendências para editais de fomento</h1>",
           f"<p class=sub>Mato Grosso · gerado em {hoje} · fontes: OpenAlex, Horizon Europe, Grants.gov, GDELT, "
           "páginas de congressos e fomento monitoradas</p>",
           "<h2>Ranking de temas</h2><table><tr><th>#</th><th>Tema</th><th>Score</th><th></th>"
           "<th>Publicações</th><th>Cresc. rel.</th><th>Chamadas int.</th><th>Mídia</th></tr>"]
    for n, (tid, r) in enumerate(df.iterrows(), 1):
        out.append(f"<tr><td>{n}</td><td><a href='#{tid}'>{e(r['tema'])}</a></td><td><b>{r['score']:.0f}</b></td>"
                   f"<td style='width:120px'><div class=bar><i style='width:{r['score']:.0f}%'></i></div></td>"
                   f"<td>{'n/d' if pd.isna(r['sci_volume']) else f'{int(r['sci_volume']):,}'.replace(',', '.')}</td>"
                   f"<td>{_pct(r['sci_growth'])}</td>"
                   f"<td>{'n/d' if pd.isna(r['funding']) else int(r['funding'])}</td>"
                   f"<td>{_pct(r['media_tendencia'])}</td></tr>")
    out.append("</table>")

    out.append("<h2>Detalhe por tema</h2>")
    for tid, r in df.iterrows():
        t = by_id[tid]
        out.append(f"<div class=card id={tid}><h3>{e(t['nome'])} <span class=tag>score {r['score']:.0f}</span></h3>")
        out.append("<ul>" + "".join(f"<li>{e(b)}</li>" for b in _porque(r, ciencia, editais, midia, web, tid, trends)) + "</ul>")
        out.append(f"<div class=sug><b>Sugestão de linha de edital (MT):</b> {e(t['edital_mt'])}</div>")
        ed = (editais or {}).get(tid)
        if ed and ed["chamadas"]:
            out.append("<b>Chamadas internacionais de referência</b><ul>")
            for c in ed["chamadas"][:5]:
                out.append(f"<li><a href='{e(c['url'])}'>{e(c['titulo'] or c['id'])}</a> "
                           f"<small>· {e(c['fonte'])} · prazo {c['prazo'] or 'n/d'}</small></li>")
            out.append("</ul>")
        c = (ciencia or {}).get(tid)
        if c and c["top_works"]:
            out.append("<b>Trabalhos mais citados (últimos 2 anos)</b><ul>")
            for w in c["top_works"][:3]:
                link = w["doi"] or "#"
                out.append(f"<li><a href='{e(link)}'>{e(w['titulo'] or '')}</a> "
                           f"<small>· {e(w['veiculo'] or '')} · {w['citacoes']} citações</small></li>")
            out.append("</ul>")
        m = (midia or {}).get(tid)
        if m and m["manchetes"]:
            out.append("<b>Manchetes recentes</b><ul>")
            for h in m["manchetes"][:4]:
                out.append(f"<li><a href='{e(h['url'])}'>{e(h['titulo'] or '')}</a> <small>· {e(h['dominio'] or '')}</small></li>")
            out.append("</ul>")
        g = (trends or {}).get(tid)
        if g and g["consultas"]:
            out.append("<b>Buscas relacionadas em alta (Google Trends)</b><ul><li>" +
                       "</li><li>".join(f"{e(q['consulta'])} <small>· {'em alta' if q['tipo'] == 'rising' else 'mais buscada'}</small>"
                                        for q in g["consultas"]) + "</li></ul>")
        w = (web or {}).get(tid)
        if w and w["itens"]:
            out.append("<b>Menções em congressos/fomento/notícias</b><ul>")
            for it in w["itens"][:4]:
                out.append(f"<li><a href='{e(it['url'])}'>{e(it['texto'][:140])}</a> <small>· {e(it['fonte'])}</small></li>")
            out.append("</ul>")
        out.append("</div>")

    out.append("<h2>Metodologia e limites</h2><ul>"
               "<li>Score 0–100 = média ponderada de percentis entre os temas (pesos em <code>config.yaml</code>).</li>"
               "<li>Crescimento relativo = variação da participação do tema no total de publicações (OpenAlex) entre "
               "dois anos completos, o que elimina o efeito do crescimento geral da ciência.</li>"
               "<li>Congressos: trabalhos indexados como anais (OpenAlex) + páginas de eventos monitoradas.</li>"
               "<li>Os percentis são relativos à lista de temas escolhida: o ranking mostra prioridade relativa, não valor absoluto.</li>"
               "<li>Mídia: GDELT quando disponível para todos os temas; caso contrário Google News RSS (máx. ~100 itens por consulta, temas muito quentes saturam). Ambos em inglês.</li><li>Google Trends é API não oficial e normaliza cada termo por si: serve para tendência, não para comparar volume entre temas.</li></ul>")
    out.append("<h3>Status das fontes web</h3><ul>" +
               "".join(f"<li>{e(k)}: {v} itens lidos {'⚠️' if v == 0 else ''}</li>" for k, v in status_web.items()) + "</ul>")
    path.write_text("\n".join(out), encoding="utf-8")


def excel(df, temas, ciencia, editais, midia, web, path: pathlib.Path, trends=None) -> None:
    by_id = {t["id"]: t for t in temas}
    ranking = df.reset_index().rename(columns={
        "tema": "Tema", "score": "Score", "sci_volume": "Publicações (ano ref.)",
        "sci_growth": "Cresc. relativo ciência", "conf_volume": "Trabalhos em congressos",
        "conf_growth": "Cresc. relativo congressos", "funding": "Chamadas int. abertas",
        "media_intensidade": "Mídia: intensidade", "media_tendencia": "Mídia: tendência", "trends": "Google Trends: tendência",
        "web": "Menções web", "mt_fit": "Aderência MT (1-5)"})
    ranking["Sugestão de edital MT"] = ranking["id"].map(lambda i: by_id[i]["edital_mt"])
    chamadas = [{"Tema": by_id[tid]["nome"], **{k: c[k] for k in ("fonte", "titulo", "prazo", "tipo", "url")}}
                for tid, d in (editais or {}).items() for c in d["chamadas"]]
    mencoes = [{"Tema": by_id[tid]["nome"], "Fonte": it["fonte"], "Categoria": it["categoria"],
                "Texto": it["texto"], "URL": it["url"]} for tid, d in (web or {}).items() for it in d["itens"]]
    manchetes = [{"Tema": by_id[tid]["nome"], "Título": h["titulo"], "Domínio": h["dominio"], "URL": h["url"]}
                 for tid, d in (midia or {}).items() for h in d["manchetes"]]
    buscas = [{"Tema": by_id[tid]["nome"], "Termo-base": d["termo"], **q} for tid, d in (trends or {}).items() for q in d["consultas"]]
    papers = [{"Tema": by_id[tid]["nome"], **w} for tid, d in (ciencia or {}).items() for w in d["top_works"]]
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        for nome, dados in (("Ranking", ranking), ("Chamadas internacionais", pd.DataFrame(chamadas)),
                            ("Menções web", pd.DataFrame(mencoes)), ("Manchetes", pd.DataFrame(manchetes)),
                            ("Trabalhos citados", pd.DataFrame(papers)),
                            ("Buscas Google em alta", pd.DataFrame(buscas))):
            dados.to_excel(xw, sheet_name=nome, index=False)
            ws = xw.sheets[nome]
            ws.freeze_panes = "A2"
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(
                    60, max(10, max(len(str(c.value or "")) for c in col[:30]) + 2))


def historico(df, out_dir: pathlib.Path) -> None:
    f = out_dir / "historico_scores.csv"
    novo = df[["tema", "score"]].assign(data=dt.date.today().isoformat()).reset_index()
    if f.exists():
        novo = pd.concat([pd.read_csv(f), novo]).drop_duplicates(["data", "id"], keep="last")
    novo.to_csv(f, index=False, encoding="utf-8-sig")


def dump(path: pathlib.Path, **blocos) -> None:
    path.write_text(json.dumps(blocos, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
