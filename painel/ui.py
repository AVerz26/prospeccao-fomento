"""Identidade visual e componentes reutilizáveis."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

VERDE = "#1F7A5A"
VERDE_ESCURO = "#0F4C3A"
VERDE_CLARO = "#9FD3BC"
AMBAR = "#E0A030"
AZUL = "#2F6F9F"
CINZA = "#8A948F"
CINZA_CLARO = "#D9E0DC"
ESCALA = [[0, "#EAF4EE"], [0.35, "#9FD3BC"], [0.7, "#3E9A74"], [1, "#0F4C3A"]]
ESTAGIOS = {"Nascente": AMBAR, "Em aceleração": VERDE, "Incipiente": CINZA, "Estabelecida": CINZA_CLARO}

CSS = """
<style>
.block-container {padding-top: 2.2rem; max-width: 1280px;}
h1 {font-weight: 700; letter-spacing: -0.02em; margin-bottom: .1rem;}
h2, h3 {letter-spacing: -0.01em;}
[data-testid="stMetricValue"] {font-size: 1.65rem;}
[data-testid="stMetricLabel"] p {color: #5F6B66; font-size: .85rem;}
.sub {color: #5F6B66; margin: -.2rem 0 1.1rem 0; font-size: .98rem;}
.chip {display:inline-block; padding: 2px 11px; border-radius: 999px; background:#E6F2EC; color:#0F4C3A;
       font-size:.8rem; margin: 0 6px 6px 0; border: 1px solid #CFE5D9;}
.chip.alt {background:#FBF1DC; color:#6B4A0B; border-color:#F1DDAE;}
.destaque {border-left: 4px solid #1F7A5A; background:#F2F8F4; padding: .8rem 1rem; border-radius: 4px; color:#1E2A25;}
.nota {color:#5F6B66; font-size:.85rem;}
div[data-testid="stTabs"] button p {font-size: .95rem;}
</style>
"""


def injetar_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def titulo(texto: str, subtitulo: str = "") -> None:
    st.title(texto)
    if subtitulo:
        st.markdown(f'<div class="sub">{subtitulo}</div>', unsafe_allow_html=True)


def chips(itens, alt: bool = False) -> None:
    itens = [i for i in itens if i]
    if itens:
        cls = "chip alt" if alt else "chip"
        st.markdown("".join(f'<span class="{cls}">{i}</span>' for i in itens), unsafe_allow_html=True)


def destaque(texto: str) -> None:
    st.markdown(f'<div class="destaque">{texto}</div>', unsafe_allow_html=True)


def nota(texto: str) -> None:
    st.markdown(f'<span class="nota">{texto}</span>', unsafe_allow_html=True)


# ------------------------------------------------------------- formatação --
def n0(x) -> str:
    if x is None or pd.isna(x):
        return "—"
    return f"{x:,.0f}".replace(",", ".")


def n1(x) -> str:
    if x is None or pd.isna(x):
        return "—"
    return f"{x:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, sinal: bool = False) -> str:
    if x is None or pd.isna(x):
        return "—"
    return (f"{x:+.0%}" if sinal else f"{x:.0%}").replace(".", ",")


def usd(x) -> str:
    if x is None or pd.isna(x) or x == 0:
        return "—"
    if abs(x) >= 1e9:
        return f"US$ {x / 1e9:.1f} bi".replace(".", ",")
    return f"US$ {x / 1e6:,.0f} mi".replace(",", ".")


def curto(s: str, n: int = 52) -> str:
    s = str(s)
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def bolinhas(valor, total: int = 5) -> str:
    if valor is None or pd.isna(valor):
        return "—"
    v = int(round(valor))
    return "●" * v + "○" * (total - v)


# ------------------------------------------------------------------ gráficos --
def estilo(fig: go.Figure, altura: int = 380, legenda: bool = False) -> go.Figure:
    fig.update_layout(
        height=altura, margin=dict(l=0, r=10, t=10, b=0), showlegend=legenda,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13), hoverlabel=dict(font_size=13),
    )
    if legenda:
        fig.update_layout(legend=dict(orientation="h", y=-0.12, x=0))
    fig.update_xaxes(showgrid=True, gridcolor="rgba(128,140,134,.18)", zeroline=False)
    fig.update_yaxes(showgrid=False, zeroline=False)
    return fig


def mostrar(fig: go.Figure, chave: str | None = None) -> None:
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=chave)


def barras_h(df: pd.DataFrame, rotulo: str, valor: str, cor=VERDE, altura: int | None = None,
             texto_fmt: str = ",.0f", hover: str | None = None) -> go.Figure:
    d = df.iloc[::-1]
    fig = go.Figure(go.Bar(
        x=d[valor], y=[curto(x, 46) for x in d[rotulo]], orientation="h",
        marker_color=cor if isinstance(cor, str) else list(cor)[::-1],
        text=d[valor], texttemplate="%{text:" + texto_fmt + "}", textposition="outside", cliponaxis=False,
        customdata=d[hover] if hover else d[rotulo],
        hovertemplate="%{customdata}<br><b>%{x:" + texto_fmt + "}</b><extra></extra>",
    ))
    fig.update_xaxes(showticklabels=False, showgrid=False)
    return estilo(fig, altura or max(180, 34 * len(d) + 30))


def radar(series: list[tuple[str, list[float | None], str, bool]], rotulos: list[str], altura: int = 400) -> go.Figure:
    """series: (nome, valores 0-100, cor, tracejado)."""
    fig = go.Figure()
    for nome, vals, cor, tracejado in series:
        v = [0 if x is None or pd.isna(x) else x for x in vals]
        fig.add_trace(go.Scatterpolar(
            r=v + v[:1], theta=rotulos + rotulos[:1], name=nome, mode="lines" + ("" if tracejado else "+markers"),
            line=dict(color=cor, width=2, dash="dash" if tracejado else "solid"),
            fill=None if tracejado else "toself", fillcolor=_alpha(cor, .18),
            hovertemplate="%{theta}: <b>%{r:.0f}</b><extra>" + nome + "</extra>",
        ))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0, 100], tickvals=[25, 50, 75], showline=False,
                                                 gridcolor="rgba(128,140,134,.25)"),
                                 angularaxis=dict(gridcolor="rgba(128,140,134,.25)"), bgcolor="rgba(0,0,0,0)"))
    return estilo(fig, altura, legenda=len(series) > 1).update_layout(margin=dict(l=70, r=70, t=20, b=30))


def _alpha(hex_cor: str, a: float) -> str:
    h = hex_cor.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{a})"
