"""Radar tecnológico: tecnologias emergentes em estágio inicial."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import dados
import ui

ESTAGIO_TEXTO = {
    "Nascente": "volume baixo e crescimento alto",
    "Em aceleração": "crescimento alto com volume já relevante",
    "Incipiente": "volume baixo, ainda sem tração",
    "Estabelecida": "tecnologia consolidada",
}
# (rótulo, coluna atual, coluna anterior)
PARES = [
    ("Preprints (OpenAlex, 6 meses)", "Preprints OpenAlex (6m)", "Preprints OpenAlex (6m ant.)"),
    ("Preprints (arXiv, 6 meses)", "arXiv (6m)", "arXiv (6m ant.)"),
    ("Repositórios novos (GitHub, 12 meses)", "Repos GitHub novos (12m)", "Repos GitHub (12m ant.)"),
]


def pagina() -> None:
    ex = dados.atual()
    ui.titulo("Radar tecnológico",
              "Tecnologias em estágio inicial: pouco volume e crescimento alto. Critério oposto ao do ranking de temas.")
    r = ex.aba("Radar emergentes")
    if r.empty:
        st.info("Esta execução não inclui o radar de tecnologias emergentes.")
        return
    r = r.sort_values("Score", ascending=False).reset_index(drop=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Tecnologias no radar", len(r))
    c2.metric("Em aceleração", int((r["Estágio"] == "Em aceleração").sum()))
    c3.metric("Nascentes", int((r["Estágio"] == "Nascente").sum()))

    st.markdown("**Ranking**")
    cores = [ui.ESTAGIOS.get(e, ui.CINZA) for e in r["Estágio"]]
    fig = ui.barras_h(r, "Tecnologia", "Score", cor=cores, texto_fmt=".1f", hover="Tecnologia", altura=34 * len(r) + 30)
    fig.update_xaxes(range=[0, 100])
    ui.mostrar(fig, "radar_rank")
    ui.chips([f"<b>{e}</b>: {t}" for e, t in ESTAGIO_TEXTO.items()], alt=False)

    st.divider()
    rotulos = {f"#{i + 1} · {x.Tecnologia}": x.Tecnologia for i, x in enumerate(r.itertuples())}
    tech = rotulos[st.selectbox("Tecnologia", list(rotulos), label_visibility="collapsed")]
    t = r[r["Tecnologia"] == tech].iloc[0]

    st.subheader(tech)
    a, b, c, d = st.columns(4)
    a.metric("Score", ui.n1(t["Score"]))
    b.metric("Estágio", t["Estágio"], help=ESTAGIO_TEXTO.get(t["Estágio"], ""))
    c.metric("Aderência a MT", ui.bolinhas(t["Aderência MT"]))
    d.metric("Publicações (12m)", ui.n0(t["Publicações totais (12m)"]), help="Quanto menor, mais imatura a tecnologia")

    e, f = st.columns([5, 4], gap="large")
    with e:
        st.markdown("**Atividade: semestre/ano atual vs. anterior**")
        atual = [t[c_] for _, c_, _ in PARES]
        antes = [t[p] for _, _, p in PARES]
        fig = go.Figure([
            go.Bar(name="Anterior", x=[x for x, _, _ in PARES], y=antes, marker_color=ui.CINZA_CLARO, text=antes, textposition="outside"),
            go.Bar(name="Atual", x=[x for x, _, _ in PARES], y=atual, marker_color=ui.VERDE, text=atual, textposition="outside"),
        ])
        fig.update_layout(barmode="group")
        fig.update_yaxes(showticklabels=False, showgrid=False)
        ui.mostrar(ui.estilo(fig, 320, legenda=True), "radar_pares")
    with f:
        st.markdown("**Outros sinais**")
        g, h = st.columns(2)
        g.metric("Hugging Face (90d)", ui.n0(t["HF modelos+datasets (90d)"]), help="Modelos e datasets novos")
        h.metric("Startups Y Combinator", ui.n0(t["Startups YC"]))
        g.metric("Menções AgFunder", ui.n0(t["Menções AgFunder"]))
        h.metric("Horizon (pesquisa inicial)", ui.n0(t["Horizon pesquisa inicial"]), help=f"Total de chamadas Horizon: {ui.n0(t['Horizon total'])}")

    ex_df = ex.aba("Radar exemplos")
    ex_df = ex_df[ex_df["Tecnologia"] == tech] if not ex_df.empty else ex_df
    st.markdown(f"**Exemplos encontrados ({len(ex_df)})**")
    if ex_df.empty:
        st.info("Sem exemplos listados.")
    else:
        nomes = {"arxiv": "arXiv", "github": "GitHub", "huggingface": "Hugging Face", "yc": "Y Combinator",
                 "agfunder": "AgFunder", "openalex": "OpenAlex", "horizon": "Horizon Europe"}
        for fonte, g in ex_df.groupby("Fonte"):
            with st.expander(f"{nomes.get(str(fonte).lower(), fonte)} ({len(g)})"):
                for x in g.head(8).itertuples():
                    detalhe = f" · {x.Detalhe}" if isinstance(x.Detalhe, str) and x.Detalhe else ""
                    st.markdown(f"- [{ui.curto(x.Item, 120)}]({x.URL}){detalhe}")
        ui.nota("Contagens pequenas oscilam muito: leia os exemplos antes de decidir.")
