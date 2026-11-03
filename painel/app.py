"""Painel da prospecção de tendências para fomento (Mato Grosso).

Executar:  streamlit run painel/app.py
Lê as execuções em resultados/<data>/prospeccao.xlsx (e dados.json, se existir).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # permite `import dados`/`ui` e o pacote paginas

import streamlit as st  # noqa: E402

st.set_page_config(page_title="Prospecção de fomento · MT", page_icon=":material/radar:", layout="wide")

import dados  # noqa: E402
import ui  # noqa: E402
from paginas import areas, metodologia, panorama, radar, temas, territorio  # noqa: E402

ui.injetar_css()

execucoes = dados.listar_execucoes()
if not execucoes:
    st.error("Nenhuma execução encontrada em `resultados/`. Rode a prospecção (`python run.py`) ou o workflow do GitHub.")
    st.stop()

with st.sidebar:
    st.markdown("### Prospecção de fomento")
    st.caption("Tendências científicas, tecnológicas e de financiamento para Mato Grosso")
    rotulos = {f"{panorama.data_br(k)}" + ("  ·  mais recente" if i == 0 else ""): k for i, k in enumerate(execucoes)}
    escolha = st.selectbox("Execução", list(rotulos), help="Cada segunda-feira o workflow gera uma nova execução.")
    chave = rotulos[escolha]

st.session_state["execucao"] = dados.Execucao(chave, execucoes[chave])

navegacao = st.navigation({
    "Visão geral": [st.Page(panorama.pagina, title="Panorama", icon=":material/dashboard:", url_path="panorama", default=True)],
    "Aprofundar": [
        st.Page(areas.pagina, title="Áreas de fomento", icon=":material/account_tree:", url_path="areas"),
        st.Page(temas.pagina, title="Temas e tendências", icon=":material/trending_up:", url_path="temas"),
        st.Page(radar.pagina, title="Radar tecnológico", icon=":material/rocket_launch:", url_path="radar"),
        st.Page(territorio.pagina, title="Mato Grosso em dados", icon=":material/landscape:", url_path="territorio"),
    ],
    "Sobre": [st.Page(metodologia.pagina, title="Metodologia e fontes", icon=":material/menu_book:", url_path="metodologia")],
})
navegacao.run()
