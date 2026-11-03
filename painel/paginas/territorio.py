"""Mato Grosso em dados: indicadores do IBGE e focos de calor do INPE."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import dados
import ui

PALETA = {"Amazônia": ui.VERDE, "Cerrado": ui.AMBAR, "Pantanal": ui.AZUL, "Mata Atlântica": ui.VERDE_CLARO,
          "Caatinga": "#B5523B", "Pampa": ui.CINZA}


def pagina() -> None:
    ex = dados.atual()
    ui.titulo("Mato Grosso em dados", "O território por trás das áreas de fomento: produção agropecuária (IBGE) e fogo (INPE).")
    ibge, focos = ex.aba("Dossiê Território IBGE"), ex.aba("Dossiê Focos INPE")
    if ibge.empty and focos.empty:
        st.info("Esta execução não inclui os indicadores de território.")
        return

    if not ibge.empty:
        st.subheader("Produção agropecuária")
        prod = ibge[ibge["Indicador"].str.contains("quantidade produzida|Rebanho", case=False)]
        cols = st.columns(max(1, len(prod)))
        for col, x in zip(cols, prod.itertuples()):
            nome = x.Indicador.split("—")[0].strip()
            col.metric(nome, ui.n0(x.MT), delta=f"{ui.pct(x._6, True)} desde {x._7}" if pd.notna(x._6) else None,
                       help=f"{x.Indicador} · {ui.pct(x._5)} do Brasil em {x.Ano}")
        st.markdown("**Participação de Mato Grosso no Brasil**")
        p = ibge.copy()
        p["Participação"] = p["Participação MT"]
        fig = ui.barras_h(p.sort_values("Participação", ascending=False), "Indicador", "Participação",
                          texto_fmt=".0%", hover="Indicador", altura=34 * len(p) + 30)
        fig.update_xaxes(range=[0, 0.7])
        ui.mostrar(fig, "ibge_part")
        with st.expander("Tabela completa"):
            st.dataframe(ibge, hide_index=True, width="stretch", column_config={
                "MT": st.column_config.NumberColumn(format="%d"), "Brasil": st.column_config.NumberColumn(format="%d"),
                "Participação MT": st.column_config.NumberColumn(format="percent"),
                "Variação MT desde": st.column_config.NumberColumn(format="percent")})

    if not focos.empty:
        st.subheader("Focos de calor")
        mt = focos[focos["Recorte"] == "MT"].pivot_table(index="Ano", columns="Bioma", values="Focos", aggfunc="sum").sort_index()
        br = focos[focos["Recorte"] == "BR"].groupby("Ano")["Focos"].sum()
        e, d = st.columns([3, 2], gap="large")
        with e:
            st.markdown("**Mato Grosso, por bioma**")
            fig = go.Figure([go.Bar(x=[str(i) for i in mt.index], y=mt[b], name=b, marker_color=PALETA.get(b, ui.CINZA)) for b in mt.columns])
            fig.update_layout(barmode="stack")
            ui.mostrar(ui.estilo(fig, 340, legenda=True), "focos_mt")
        with d:
            st.markdown("**Participação de MT nos focos do Brasil**")
            total_mt = mt.sum(axis=1)
            share = (total_mt / br.reindex(total_mt.index)).dropna()
            fig = go.Figure(go.Scatter(x=[str(i) for i in share.index], y=share.values, mode="lines+markers",
                                       line=dict(color=ui.AMBAR, width=3), text=[f"{v:.0%}" for v in share.values],
                                       hovertemplate="%{x}: <b>%{text}</b><extra></extra>"))
            fig.update_yaxes(tickformat=".0%", rangemode="tozero")
            ui.mostrar(ui.estilo(fig, 340), "focos_share")
        ui.nota("Satélite de referência do INPE. Anos fechados são guardados em cache; o ano corrente fica de fora.")
