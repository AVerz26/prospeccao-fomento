"""Metodologia, fontes e downloads."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

import dados
import ui

REPO = "https://github.com/AVerz26/prospeccao-fomento"
PESOS_ROTULO = {
    "sci_volume": "Volume científico", "sci_growth": "Crescimento na ciência", "conf_volume": "Volume em congressos",
    "conf_growth": "Crescimento em congressos", "funding": "Chamadas internacionais", "media": "Mídia",
    "web": "Menções na web", "trends": "Google Trends", "mt_fit": "Aderência a Mato Grosso",
}


def pagina() -> None:
    ex = dados.atual()
    ui.titulo("Metodologia e fontes", "Como o score é calculado, de onde vêm os dados e como baixar os arquivos desta execução.")

    pesos = dados.config().get("pesos", {})
    e, d = st.columns([3, 2], gap="large")
    with e:
        st.subheader("Score dos temas")
        st.markdown("O score (0–100) é a **média ponderada de percentis** de nove componentes, calculados entre os temas "
                    "monitorados. Quando uma fonte está fora do ar, o peso dela é redistribuído entre as demais.")
        if pesos:
            df = pd.DataFrame({"Componente": [PESOS_ROTULO.get(k, k) for k in pesos], "Peso": list(pesos.values())})
            df = df.sort_values("Peso", ascending=False)
            fig = ui.barras_h(df, "Componente", "Peso", altura=34 * len(df) + 30, texto_fmt=".0%")
            fig.update_xaxes(range=[0, max(df["Peso"]) * 1.25])
            ui.mostrar(fig, "pesos")
        ui.nota("Pesos configuráveis em config.yaml. O score é relativo: compara os temas entre si, não mede mérito absoluto.")
    with d:
        st.subheader("Fontes")
        st.markdown(
            "- **OpenAlex**: publicações, congressos, capacidade das ICTs\n"
            "- **Horizon Europe e Grants.gov**: chamadas internacionais abertas\n"
            "- **Google News e Google Trends**: mídia e buscas\n"
            "- **Páginas monitoradas**: CNPq, Finep, FAPESP, Embrapii, CAPES, BNDES, FAO e outras\n"
            "- **arXiv, GitHub, Hugging Face, Y Combinator, AgFunder**: radar tecnológico\n"
            "- **IBGE (SIDRA) e INPE**: território de Mato Grosso\n"
            "- **Banco Mundial e Câmara dos Deputados**: financiamento e legislação\n")

    st.subheader("Limites")
    st.markdown("- Contagens pequenas oscilam; o crescimento é suavizado, mas leia os exemplos antes de decidir.\n"
                "- Buscas em inglês e por frase subestimam vocabulário diferente.\n"
                "- O Google Trends limita requisições, então a cobertura se completa ao longo das semanas.\n"
                "- A FAPEMAT bloqueia coleta automatizada: acompanhe os editais dela diretamente.")

    st.subheader(f"Arquivos desta execução ({ex.data})")
    cols = st.columns(3)
    rotulos = {"prospeccao.xlsx": ("Planilha Excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
               "relatorio.pdf": ("Relatório em PDF", "application/pdf"), "relatorio.html": ("Relatório em HTML", "text/html")}
    for col, (nome, (rot, mime)) in zip(cols, rotulos.items()):
        caminho = ex.arquivos.get(nome)
        if caminho:
            col.download_button(rot, Path(caminho).read_bytes(), file_name=f"{ex.data}_{nome}", mime=mime, width="stretch")
        else:
            col.button(f"{rot} (indisponível)", disabled=True, width="stretch")
    st.markdown(f"Código e configuração: [{REPO.split('github.com/')[1]}]({REPO})")
