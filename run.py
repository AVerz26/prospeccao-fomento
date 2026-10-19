"""Uso: python run.py [--skip ciencia,editais,midia,web] [--temas id1,id2] [--no-cache]"""
from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import pathlib

import yaml

from prospeccao import analise, ciencia, dossie, dossie_relatorio, editais, emergentes, google, midia, pdf, radar_relatorio, relatorio, web
from prospeccao.util import ROOT, Http


def carregar_env() -> None:
    """Lê KEY=VALOR de .env (sem sobrescrever variáveis já definidas)."""
    f = ROOT / ".env"
    if f.exists():
        for ln in f.read_text(encoding="utf-8").splitlines():
            if "=" in ln and not ln.lstrip().startswith("#"):
                k, v = ln.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def main() -> None:
    carregar_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip", default="", help="fontes a pular: ciencia,editais,midia,gnews,trends,web,radar,dossie")
    ap.add_argument("--temas", default="", help="limitar a alguns ids de tema (teste rápido)")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--radar-tudo", action="store_true", help="com --temas, roda todas as tecnologias do radar mesmo assim")
    ap.add_argument("--cache-horas", type=float, default=12, help="validade do cache HTTP (padrão 12)")
    ap.add_argument("--config", default=str(ROOT / "config.yaml"))
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

    cfg = yaml.safe_load(pathlib.Path(a.config).read_text(encoding="utf-8"))
    for t in cfg["temas"]:  # frases extras entram nas consultas das APIs; termos_amplos só no casamento web
        t["keywords_en"] = t["keywords_en"] + t.pop("extra_en", [])
        t["keywords_pt"] = t["keywords_pt"] + t.pop("extra_pt", [])
    temas = [t for t in cfg["temas"] if not a.temas or t["id"] in a.temas.split(",")]
    skip = set(filter(None, a.skip.split(",")))
    http = Http(ttl_hours=a.cache_horas, use_cache=not a.no_cache)

    sci = None if "ciencia" in skip else ciencia.coletar(http, temas)
    edt = None if "editais" in skip else editais.coletar(http, temas)
    med = None if "midia" in skip else midia.coletar(http, temas, cfg["gdelt"]["timespan"],
                                                     cfg["gdelt"]["headlines_por_tema"])
    # Mídia: GDELT só vale se cobrir todos os temas (senão as escalas não são comparáveis) — caso contrário Google News
    if "gnews" not in skip and (med is None or len(med) < len(temas)):
        if med:
            logging.warning("GDELT cobriu %d/%d temas — usando Google News para todos", len(med), len(temas))
        med = google.noticias(http, temas, cfg["gdelt"]["headlines_por_tema"]) or None
    trd = None if "trends" in skip else (google.trends(http, temas) or None)
    wb, status = ({}, {}) if "web" in skip else web.coletar(http, cfg["fontes_web"], temas)
    wb = wb or None

    # Radar de tecnologias emergentes (lista própria, em radar.yaml)
    radar_cfg = yaml.safe_load((ROOT / "radar.yaml").read_text(encoding="utf-8"))
    techs = [t for t in radar_cfg["tecnologias"] if not a.temas or a.radar_tudo]
    rdados = None if "radar" in skip or not techs else (emergentes.coletar(http, techs) or None)
    rdf = emergentes.calcular(techs, radar_cfg["pesos"], rdados) if rdados else None
    radar_html = radar_relatorio.html_secao(rdf, techs, rdados) if rdados else ""
    radar_abas = radar_relatorio.abas_excel(rdf, techs, rdados) if rdados else None

    # Dossiê de dados por área (areas.yaml): território, capacidade das ICTs, financiamento e legislação
    areas_cfg = yaml.safe_load((ROOT / "areas.yaml").read_text(encoding="utf-8"))
    ddados = None if "dossie" in skip or a.temas else (dossie.coletar(http, areas_cfg) or None)
    if ddados:
        radar_html += dossie_relatorio.html_secao(ddados, areas_cfg)
        radar_abas = {**(radar_abas or {}), **dossie_relatorio.abas_excel(ddados, areas_cfg)}

    df = analise.calcular(temas, cfg["pesos"], sci, edt, med, wb, trd)
    out = ROOT / "output" / dt.date.today().isoformat()
    out.mkdir(parents=True, exist_ok=True)
    relatorio.html_report(df, temas, sci, edt, med, wb, status, out / "relatorio.html", trd, radar_html)
    pdf.html_para_pdf(out / "relatorio.html", out / "relatorio.pdf")
    relatorio.excel(df, temas, sci, edt, med, wb, out / "prospeccao.xlsx", trd, radar_abas)
    relatorio.dump(out / "dados.json", ciencia=sci, editais=edt, midia=med, web=wb, trends=trd, radar=rdados, dossie=ddados)
    relatorio.historico(df, ROOT / "output")

    print("\n=== RANKING ===")
    print(df[["tema", "score"]].to_string())
    if rdf is not None:
        print("\n=== RADAR DE TECNOLOGIAS EMERGENTES ===")
        print(rdf[["tecnologia", "score", "estagio"]].to_string())
    print(f"\nRelatório: {out / 'relatorio.html'}\nPlanilha:  {out / 'prospeccao.xlsx'}")


if __name__ == "__main__":
    main()
