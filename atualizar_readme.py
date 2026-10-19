"""Atualiza a seção do último relatório no README.md. Uso: python atualizar_readme.py AAAA-MM-DD

Escreve entre os marcadores <!-- RELATORIO:INICIO --> e <!-- RELATORIO:FIM --> (cria no fim do arquivo se não existirem).
Lê o ranking de resultados/historico_scores.csv e aponta para os arquivos já copiados em resultados/.
"""
from __future__ import annotations

import csv
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
INI, FIM = "<!-- RELATORIO:INICIO -->", "<!-- RELATORIO:FIM -->"


def ranking(dia: str, n: int = 10) -> list[tuple[str, float]]:
    f = ROOT / "resultados" / "historico_scores.csv"
    if not f.exists():
        return []
    with f.open(encoding="utf-8-sig") as fh:
        linhas = [r for r in csv.DictReader(fh) if r["data"] == dia]
    return sorted(((r["tema"], float(r["score"])) for r in linhas), key=lambda x: -x[1])[:n]


def bloco(dia: str) -> str:
    pasta = f"resultados/{dia}"
    out = [INI, "## Último relatório", "",
           f"**Execução de {dia}** — [📄 Abrir o PDF](resultados/relatorio-atual.pdf) · "
           f"[PDF desta data]({pasta}/relatorio.pdf) · [Planilha Excel]({pasta}/prospeccao.xlsx) · "
           f"[HTML]({pasta}/relatorio.html)", ""]
    top = ranking(dia)
    if top:
        out += ["| # | Tema | Score |", "|---|---|---|"]
        out += [f"| {i} | {t} | {s:.0f} |" for i, (t, s) in enumerate(top, 1)]
        out += ["", "_Score 0–100, relativo aos temas monitorados. Metodologia no próprio PDF._"]
    out += ["", FIM]
    return "\n".join(out)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    readme = ROOT / "README.md"
    txt = readme.read_text(encoding="utf-8") if readme.exists() else ""
    novo = bloco(sys.argv[1])
    if INI in txt and FIM in txt:
        a, b = txt.index(INI), txt.index(FIM) + len(FIM)
        txt = txt[:a] + novo + txt[b:]
    else:
        txt = (txt.rstrip() + "\n\n" if txt.strip() else "") + novo
    readme.write_text(txt.rstrip() + "\n", encoding="utf-8")
    print(f"README atualizado ({sys.argv[1]}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
