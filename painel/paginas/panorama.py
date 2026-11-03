"""Panorama: ranking dos temas, mapa de calor e evolução."""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

import dados
import ui


def data_br(rotulo: str) -> str:
    p = rotulo.split("-")
    return f"{p[2]}/{p[1]}/{p[0]}" if len(p) == 3 and rotulo[:4].isdigit() else rotulo


def pagina() -> None:
    ex = dados.atual()
    r = ex.ranking
    if r.empty:
        st.error("A planilha desta execução não tem a aba Ranking.")
        return
    ui.titulo("Panorama da prospecção",
              f"Execução de {data_br(ex.data)} · {len(r)} temas monitorados"
              + (f" · {len(ex.aba('Radar emergentes'))} tecnologias no radar" if ex.tem_radar else ""))

    topo = r.iloc[0]
    sobe = r.dropna(subset=["delta"]).sort_values("delta", ascending=False)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Temas monitorados", len(r))
    c2.metric("Score do líder", ui.n1(topo["score"]), help=topo["tema"])
    c3.metric("Chamadas abertas", ui.n0(r["chamadas"].sum()), help="Chamadas internacionais abertas (Horizon Europe e Grants.gov), somadas entre os temas")
    if not sobe.empty and sobe.iloc[0]["delta"] > 0:
        c4.metric("Maior alta da semana", f"+{ui.n1(sobe.iloc[0]['delta'])}",
                  help=f"{sobe.iloc[0]['tema']} · variação do score desde {data_br(ex.semana_anterior or '')}")
        c4.caption(ui.curto(sobe.iloc[0]["tema"], 38))
    else:
        c4.metric("Maior alta da semana", "—", help="Sem execução anterior para comparar")

    aba_rank, aba_calor, aba_evol = st.tabs(["Ranking de temas", "Mapa de calor", "Evolução do score"])

    with aba_rank:
        esq, dir_ = st.columns([7, 3], gap="large")
        with esq:
            fig = ui.barras_h(r, "tema", "score", cor=_cores_score(r["score"]), texto_fmt=".1f", hover="tema",
                              altura=34 * len(r) + 30)
            fig.update_xaxes(range=[0, 100])
            ui.mostrar(fig, "rank_temas")
        with dir_:
            st.markdown("**Variação desde a semana anterior**")
            if sobe.empty:
                ui.nota("Ainda não há uma execução anterior para comparar.")
            else:
                st.markdown("Em alta")
                for _, x in sobe.head(3).iterrows():
                    st.markdown(f"▲ **{ui.n1(x['delta'])}** · {ui.curto(x['tema'], 40)}")
                st.markdown("Em queda")
                for _, x in sobe.tail(3).iloc[::-1].iterrows():
                    st.markdown(f"▼ **{ui.n1(abs(x['delta']))}** · {ui.curto(x['tema'], 40)}")
                ui.nota(f"Comparação com {data_br(ex.semana_anterior)}.")
            st.divider()
            st.markdown("**Como ler**")
            ui.nota("Score de 0 a 100: média ponderada de percentis, relativa aos temas monitorados — "
                    "não é uma medida absoluta. Abra a página **Temas e tendências** para ver o detalhe de cada um.")

    with aba_calor:
        cols = [(f"p_{k}", rot) for k, rot in dados.COMPONENTES if f"p_{k}" in r]
        z = r[[c for c, _ in cols]].astype(float)
        fig = go.Figure(go.Heatmap(
            z=z.values, x=[rot for _, rot in cols], y=[ui.curto(t, 50) for t in r["tema"]],
            colorscale=ui.ESCALA, zmin=0, zmax=100, xgap=2, ygap=2,
            text=z.round(0).astype("Int64").astype(str).replace("<NA>", "—").values, texttemplate="%{text}",
            hovertemplate="%{y}<br>%{x}: <b>%{z:.0f}</b><extra></extra>", colorbar=dict(title="Percentil", thickness=12),
        ))
        fig.update_yaxes(autorange="reversed")
        fig.update_xaxes(side="top", tickangle=-30)
        ui.mostrar(ui.estilo(fig, 34 * len(r) + 110), "calor")
        ui.nota("Cada célula é o percentil (0–100) do tema naquele componente. Células vazias = fonte sem dado nesta semana.")

    with aba_evol:
        h = ex.hist
        if h.empty or h["data"].nunique() < 2:
            st.info("O histórico precisa de pelo menos duas execuções para desenhar a evolução.")
        else:
            padrao = list(r["tema"].head(5))
            sel = st.multiselect("Temas", sorted(h["tema"].unique()), default=[t for t in padrao if t in set(h["tema"])])
            d = h[h["tema"].isin(sel)].sort_values("data")
            fig = px.line(d, x="data", y="score", color="tema", markers=True,
                          color_discrete_sequence=[ui.VERDE, ui.AMBAR, ui.AZUL, ui.VERDE_ESCURO, ui.CINZA, "#B5523B", "#7A5BD0"])
            fig.update_traces(line=dict(width=2.5))
            fig.update_yaxes(title=None)
            fig.update_xaxes(title=None, type="category")
            ui.mostrar(ui.estilo(fig, 420, legenda=True), "evolucao")


def _cores_score(s):
    """Verde mais escuro para scores mais altos (escala fixa 40–80)."""
    base = ["#CFE5D9", "#9FD3BC", "#6DB993", "#3E9A74", "#1F7A5A", "#0F4C3A"]
    out = []
    for v in s:
        i = min(len(base) - 1, max(0, int((v - 40) / 8)))
        out.append(base[i])
    return out
