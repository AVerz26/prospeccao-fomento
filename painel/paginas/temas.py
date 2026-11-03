"""Temas e tendências: detalhe de cada um dos temas do ranking."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import dados
import ui

FORTE, FRACO = 75, 25


def pagina() -> None:
    ex = dados.atual()
    r = ex.ranking
    if r.empty:
        st.error("A planilha desta execução não tem a aba Ranking.")
        return
    ui.titulo("Temas e tendências", "Cada tema monitorado em detalhe: o que sustenta o score e o que há de oportunidade.")

    rotulos = {f"#{x.posicao} · {x.tema}": x.tema for x in r.itertuples()}
    escolha = st.selectbox("Tema", list(rotulos), label_visibility="collapsed")
    tema = rotulos[escolha]
    t = r[r["tema"] == tema].iloc[0]
    cfg_t = next((x for x in dados.config().get("temas", []) if x.get("id") == t["id"]), {})

    st.subheader(tema)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Score", ui.n1(t["score"]),
              delta=None if pd.isna(t.get("delta")) else f"{t['delta']:+.1f} na semana")
    c2.metric("Posição", f"{t['posicao']}º de {len(r)}")
    c3.metric("Aderência a MT", ui.bolinhas(t["mt_fit"]), help="Escala de 1 a 5, definida em config.yaml")
    c4.metric("Chamadas abertas", ui.n0(t["chamadas"]), help="Chamadas internacionais abertas (Horizon Europe e Grants.gov)")

    esq, dir_ = st.columns([5, 4], gap="large")
    with esq:
        comp = [(k, rot) for k, rot in dados.COMPONENTES if f"p_{k}" in r]
        rot_c = [dados.ROTULO_CURTO[k] for k, _ in comp]
        mediana = [r[f"p_{k}"].median() for k, _ in comp]
        meu = [t[f"p_{k}"] for k, _ in comp]
        fig = ui.radar([(ui.curto(tema, 28), meu, ui.VERDE, False), ("Mediana dos temas", mediana, ui.CINZA, True)], rot_c)
        ui.mostrar(fig, f"radar_{t['id']}")
    with dir_:
        pares = sorted(((rot, t[f"p_{k}"]) for k, rot in comp if pd.notna(t[f"p_{k}"])), key=lambda x: -x[1])
        fortes = [f"**{n}** ({v:.0f})" for n, v in pares if v >= FORTE]
        fracos = [f"**{n}** ({v:.0f})" for n, v in pares[::-1] if v <= FRACO]
        st.markdown("**Pontos fortes**")
        st.markdown(" · ".join(fortes[:4]) if fortes else "Nenhum componente acima do percentil 75.")
        st.markdown("**Pontos de atenção**")
        st.markdown(" · ".join(fracos[:4]) if fracos else "Nenhum componente abaixo do percentil 25.")
        ui.nota("Entre parênteses, o percentil (0–100) entre os temas.")
        st.markdown("&nbsp;")
        st.markdown("**Números**")
        a, b = st.columns(2)
        a.metric("Publicações (ano ref.)", ui.n0(t["sci_vol"]), delta=ui.pct(t["sci_cresc"], True) if pd.notna(t["sci_cresc"]) else None,
                 help="Delta: crescimento relativo da participação do tema na ciência")
        b.metric("Trabalhos em congressos", ui.n0(t["conf_vol"]), delta=ui.pct(t["conf_cresc"], True) if pd.notna(t["conf_cresc"]) else None)
        a.metric("Mídia (notícias recentes)", ui.n0(t["midia_int"]), delta=ui.pct(t["midia_tend"], True) if pd.notna(t["midia_tend"]) else None,
                 help="Delta: 30 dias vs. 30 dias anteriores")
        b.metric("Menções na web", ui.n0(t["web"]))
        a.metric("Google Trends (12 meses)", ui.pct(t["trends"], True))

    edital = t.get("edital_mt") or cfg_t.get("edital_mt")
    if isinstance(edital, str) and edital.strip():
        st.markdown("**Oportunidade de edital em Mato Grosso**")
        ui.destaque(edital)

    _abas_detalhe(ex, tema, cfg_t)


def _abas_detalhe(ex: dados.Execucao, tema: str, cfg_t: dict) -> None:
    def do_tema(nome: str) -> pd.DataFrame:
        d = ex.aba(nome)
        return d[d["Tema"] == tema] if not d.empty and "Tema" in d else pd.DataFrame()

    cham, lit, mid = do_tema("Chamadas internacionais"), do_tema("Trabalhos citados"), do_tema("Manchetes")
    web, bus = do_tema("Menções web"), do_tema("Buscas Google em alta")
    abas = st.tabs([f"Chamadas ({len(cham)})", f"Literatura ({len(lit)})", f"Mídia ({len(mid)})",
                    f"Web ({len(web)})", f"Buscas ({len(bus)})", "Palavras-chave"])

    with abas[0]:
        if cham.empty:
            st.info("Nenhuma chamada internacional aberta para este tema nesta execução.")
        else:
            d = cham.copy()
            d["dias"] = d["prazo"].map(dados.dias_ate)
            d = d.sort_values("prazo", na_position="last")
            st.dataframe(
                d[["titulo", "fonte", "tipo", "prazo", "dias", "url"]], hide_index=True, width="stretch",
                column_config={
                    "titulo": st.column_config.TextColumn("Chamada", width="large"),
                    "fonte": "Fonte", "tipo": "Tipo de ação",
                    "prazo": st.column_config.DateColumn("Prazo", format="DD/MM/YYYY"),
                    "dias": st.column_config.NumberColumn("Dias", format="%d"),
                    "url": st.column_config.LinkColumn("Link", display_text="abrir"),
                })

    with abas[1]:
        if lit.empty:
            st.info("Sem trabalhos listados.")
        for x in lit.itertuples():
            st.markdown(f"**[{x.titulo}]({x.doi})**  \n{ui.n0(x.citacoes)} citações · {x.ano}"
                        + (f" · {x.veiculo}" if isinstance(x.veiculo, str) else ""))

    with abas[2]:
        if mid.empty:
            st.info("Sem manchetes.")
        for x in mid.itertuples():
            st.markdown(f"[{x.Título}]({x.URL})  \n<span class='nota'>{x.Domínio}</span>", unsafe_allow_html=True)

    with abas[3]:
        if web.empty:
            st.info("Nenhuma menção nas páginas monitoradas.")
        rot = {"fomento_br": "Fomento no Brasil", "congresso": "Congressos e eventos", "noticia": "Notícias", "ciencia": "Ciência"}
        for cat, g in web.groupby("Categoria"):
            st.markdown(f"**{rot.get(cat, cat)}** ({len(g)})")
            for x in g.head(6).itertuples():
                st.markdown(f"- [{x.Fonte}]({x.URL}): {ui.curto(x.Texto, 220)}")

    with abas[4]:
        if bus.empty:
            st.info("Sem buscas em alta (o Google Trends limita requisições; a cobertura completa vem ao longo das semanas).")
        else:
            d = bus.sort_values("valor", ascending=False).head(10)
            fig = ui.barras_h(d, "consulta", "valor", altura=40 * len(d) + 30, hover="consulta")
            ui.mostrar(fig, "buscas")
            ui.nota("Consultas relacionadas em alta; o valor é o crescimento relativo informado pelo Google Trends.")

    with abas[5]:
        st.markdown("**Português**")
        ui.chips(cfg_t.get("keywords_pt", []) + cfg_t.get("extra_pt", []))
        st.markdown("**Inglês** (usadas nas buscas científicas)")
        ui.chips(cfg_t.get("keywords_en", []) + cfg_t.get("extra_en", []), alt=True)
        if not cfg_t:
            ui.nota("config.yaml não encontrado ou sem este tema.")
