"""Áreas de fomento: dossiê de dados de cada uma das ideias de fomento para Mato Grosso."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import dados
import ui

CULTURAS = {"soja": "Soja", "milho": "Milho", "algodao": "Algodão", "rebanho": "Rebanho"}
STATUS = {"Active": "Em execução", "Pipeline": "Em preparação", "Closed": "Encerrado", "Dropped": "Cancelado"}


def pagina() -> None:
    ex = dados.atual()
    ui.titulo("Áreas de fomento para Mato Grosso",
              "Dossiê de dados de cada área: capacidade científica das ICTs, financiamento multilateral, legislação e território.")
    if not ex.tem_dossie:
        st.info("Esta execução não inclui o dossiê de áreas. Ele passa a existir a partir da versão do coletor que gera "
                "as abas “Dossiê …” na planilha (comando `python run.py` sem `--skip dossie`).")
        return
    areas = dados.areas_cfg().get("areas", [])
    if not areas:
        st.warning("areas.yaml não encontrado.")
        return

    resumo = _resumo(ex, areas)
    aba_comp, aba_det = st.tabs(["Comparativo das áreas", "Área em detalhe"])

    with aba_comp:
        d = resumo.sort_values("mt", ascending=False)
        st.markdown("**Trabalhos científicos das ICTs de Mato Grosso (5 anos)**")
        ui.mostrar(ui.barras_h(d, "nome", "mt", altura=36 * len(d) + 30, hover="nome"), "comp_mt")
        st.markdown("**Visão geral**")
        st.dataframe(
            d[["nome", "mt", "wb_n", "wb_usd", "leg_n"]], hide_index=True, width="stretch",
            column_config={
                "nome": st.column_config.TextColumn("Área", width="large"),
                "mt": st.column_config.NumberColumn("Trabalhos de ICTs de MT", format="%d"),
                "wb_n": st.column_config.NumberColumn("Projetos Banco Mundial", format="%d"),
                "wb_usd": st.column_config.NumberColumn("Valor (US$ milhões)", format="%.0f"),
                "leg_n": st.column_config.NumberColumn("Proposições na Câmara", format="%d"),
            })
        ui.nota("Capacidade pequena em MT combinada a financiamento e legislação ativos sugere onde um edital estruturante "
                "teria mais efeito. Contagens baixas oscilam: confira os itens na aba de detalhe.")

    with aba_det:
        nomes = {a["nome"]: a for a in areas}
        escolha = st.selectbox("Área", list(nomes), label_visibility="collapsed")
        _detalhe(ex, nomes[escolha])


def _resumo(ex: dados.Execucao, areas: list[dict]) -> pd.DataFrame:
    mt, wb, leg = ex.aba("Dossiê ICTs de MT"), ex.aba("Dossiê Banco Mundial"), ex.aba("Dossiê Câmara")
    linhas = []
    for a in areas:
        j = ex.area_json(a["id"])
        n = a["nome"]
        wbn = wb[wb["Área"] == n] if not wb.empty else wb
        linhas.append({
            "id": a["id"], "nome": n,
            "mt": int(mt.loc[mt["Área"] == n, "Trabalhos (5 anos)"].sum()) if not mt.empty else 0,
            "wb_n": (j or {}).get("financiamento", {}).get("n", len(wbn)),
            "wb_usd": ((j or {}).get("financiamento", {}).get("total_usd", wbn["Valor (US$)"].sum() if not wbn.empty else 0)) / 1e6,
            "leg_n": (j or {}).get("legislacao", {}).get("n", int((leg["Área"] == n).sum()) if not leg.empty else 0),
        })
    return pd.DataFrame(linhas)


def _detalhe(ex: dados.Execucao, a: dict) -> None:
    nome, j = a["nome"], ex.area_json(a["id"])
    st.subheader(nome)
    ui.chips(a.get("pt", []))
    ui.chips(a.get("kw", []), alt=True)

    mt = ex.aba("Dossiê ICTs de MT")
    br = ex.aba("Dossiê ICTs do Brasil")
    wb = ex.aba("Dossiê Banco Mundial")
    leg = ex.aba("Dossiê Câmara")
    mt, br = mt[mt["Área"] == nome], br[br["Área"] == nome]
    wb, leg = wb[wb["Área"] == nome], leg[leg["Área"] == nome]
    cap = (j or {}).get("capacidade") or {}
    fin = (j or {}).get("financiamento") or {}
    lei = (j or {}).get("legislacao") or {}

    mt_total = int(mt["Trabalhos (5 anos)"].sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Trabalhos em MT", ui.n0(mt_total), help="Soma dos trabalhos dos últimos 5 anos nas ICTs acompanhadas")
    if cap.get("brasil_total"):
        c2.metric("Participação de MT", ui.pct(mt_total / cap["brasil_total"]), help=f"{ui.n0(cap['brasil_total'])} trabalhos no Brasil")
    else:
        c2.metric("Participação de MT", "—", help="Disponível quando a execução inclui dados.json")
    c3.metric("Banco Mundial", ui.n0(fin.get("n", len(wb))), help=ui.usd(fin.get("total_usd", wb["Valor (US$)"].sum())))
    c4.metric("Câmara", ui.n0(lei.get("n", len(leg))))

    t_cap, t_fin, t_leg, t_ter = st.tabs(["Capacidade científica", "Financiamento", "Legislação", "Território"])

    with t_cap:
        e, d = st.columns(2, gap="large")
        with e:
            st.markdown("**ICTs de Mato Grosso**")
            m = mt.sort_values("Trabalhos (5 anos)", ascending=False)
            ui.mostrar(ui.barras_h(m, "ICT de MT", "Trabalhos (5 anos)", altura=40 * len(m) + 40, hover="ICT de MT"), "cap_mt")
        with d:
            st.markdown("**Principais ICTs do Brasil**")
            b = br.sort_values("Trabalhos (5 anos)", ascending=False).head(8)
            if b.empty:
                st.info("Sem ranking nacional.")
            else:
                cores = [ui.AMBAR if str(u) == "Mato Grosso" else ui.VERDE for u in b["UF"]]
                fig = ui.barras_h(b, "ICT do Brasil", "Trabalhos (5 anos)", cor=cores, altura=40 * len(b) + 40, hover="ICT do Brasil")
                ui.mostrar(fig, "cap_br")
        if cap.get("mundo"):
            st.markdown("**Produção por ano**")
            e, d = st.columns(2, gap="large")
            for coluna, chave, titulo, cor in ((e, "mundo", "Mundo", ui.AZUL), (d, "brasil", "Brasil", ui.VERDE)):
                serie = pd.Series(cap[chave]).sort_index()
                fig = go.Figure(go.Bar(x=[str(i) for i in serie.index], y=serie.values, marker_color=cor,
                                       text=serie.values, textposition="outside", cliponaxis=False))
                fig.update_yaxes(showticklabels=False, showgrid=False)
                coluna.markdown(titulo)
                with coluna:
                    ui.mostrar(ui.estilo(fig, 230), f"serie_{chave}")
        else:
            ui.nota("As séries anuais (mundo e Brasil) aparecem quando a pasta da execução inclui o dados.json.")

    with t_fin:
        if wb.empty:
            st.info("Nenhum projeto do Banco Mundial no Brasil relevante para esta área.")
        else:
            d = wb.copy()
            d["Status"] = d["Status"].map(lambda s: STATUS.get(s, s))
            d["Valor (US$ mi)"] = d["Valor (US$)"] / 1e6
            st.dataframe(
                d[["Projeto", "Aprovado", "Valor (US$ mi)", "Status", "URL"]], hide_index=True, width="stretch",
                column_config={
                    "Projeto": st.column_config.TextColumn(width="large"),
                    "Valor (US$ mi)": st.column_config.NumberColumn(format="%.0f"),
                    "URL": st.column_config.LinkColumn("Link", display_text="abrir"),
                })
            ui.nota("Projetos do Banco Mundial no Brasil (a partir de 2015) cujo título/resumo menciona os termos da área. "
                    "Indicam onde há recurso multilateral e potencial de contrapartida; não são específicos de MT.")

    with t_leg:
        if leg.empty:
            st.info("Nenhuma proposição legislativa encontrada para os termos desta área.")
        else:
            for x in leg.itertuples():
                st.markdown(f"**[{x.Proposição}]({x.URL})**  \n{x.Ementa}")
            n = lei.get("n")
            if n and n > len(leg):
                ui.nota(f"Mostrando {len(leg)} de {n} proposições encontradas desde 2023.")

    with t_ter:
        _territorio(ex, a)


def _territorio(ex: dados.Execucao, a: dict) -> None:
    chaves = a.get("territorio", [])
    ibge, focos = ex.aba("Dossiê Território IBGE"), ex.aba("Dossiê Focos INPE")
    mostrou = False
    for k in chaves:
        if k in CULTURAS and not ibge.empty:
            d = ibge[ibge["Indicador"].str.startswith(CULTURAS[k])]
            if d.empty:
                continue
            mostrou = True
            st.markdown(f"**{CULTURAS[k]}** · IBGE")
            cols = st.columns(len(d))
            for col, x in zip(cols, d.itertuples()):
                rot = x.Indicador.split("—")[-1].strip().capitalize()
                col.metric(rot, ui.n0(x.MT), delta=f"{ui.pct(x._6, True)} desde {x._7}" if pd.notna(x._6) else None,
                           help=f"{ui.pct(x._5)} do Brasil em {x.Ano}")
        elif k == "focos" and not focos.empty:
            mostrou = True
            st.markdown("**Focos de calor em Mato Grosso por bioma** · INPE")
            _grafico_focos(focos)
    if not mostrou:
        st.info("Esta área não tem indicador de território associado.")


def _grafico_focos(focos: pd.DataFrame) -> None:
    mt = focos[focos["Recorte"] == "MT"].pivot_table(index="Ano", columns="Bioma", values="Focos", aggfunc="sum").sort_index()
    paleta = {"Amazônia": ui.VERDE, "Cerrado": ui.AMBAR, "Pantanal": ui.AZUL}
    fig = go.Figure([go.Bar(x=[str(i) for i in mt.index], y=mt[b], name=b, marker_color=paleta.get(b, ui.CINZA)) for b in mt.columns])
    fig.update_layout(barmode="stack")
    ui.mostrar(ui.estilo(fig, 320, legenda=True), "focos_area")
