"""Uso: python run.py [--skip ciencia,editais,midia,web] [--temas id1,id2] [--no-cache]"""
from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import pathlib

import yaml

from prospeccao import analise, ciencia, editais, google, midia, pdf, relatorio, web
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
    ap.add_argument("--skip", default="", help="fontes a pular: ciencia,editais,midia,gnews,trends,web")
    ap.add_argument("--temas", default="", help="limitar a alguns ids de tema (teste rápido)")
    ap.add_argument("--no-cache", action="store_true")
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

    df = analise.calcular(temas, cfg["pesos"], sci, edt, med, wb, trd)
    out = ROOT / "output" / dt.date.today().isoformat()
    out.mkdir(parents=True, exist_ok=True)
    relatorio.html_report(df, temas, sci, edt, med, wb, status, out / "relatorio.html", trd)
    pdf.html_para_pdf(out / "relatorio.html", out / "relatorio.pdf")
    relatorio.excel(df, temas, sci, edt, med, wb, out / "prospeccao.xlsx", trd)
    relatorio.dump(out / "dados.json", ciencia=sci, editais=edt, midia=med, web=wb, trends=trd)
    relatorio.historico(df, ROOT / "output")

    print("\n=== RANKING ===")
    print(df[["tema", "score"]].to_string())
    print(f"\nRelatório: {out / 'relatorio.html'}\nPlanilha:  {out / 'prospeccao.xlsx'}")


if __name__ == "__main__":
    main()
