"""Camada de dados do painel: encontra as execuções, lê a planilha e o JSON e normaliza tudo."""
from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

RAIZ = Path(__file__).resolve().parent.parent
ENV_DADOS = "PROSPECCAO_DADOS"  # pasta extra com subpastas <execução>/prospeccao.xlsx (uso local/testes)

# (chave do percentil p_<chave>, rótulo, chave do peso em config.yaml)
COMPONENTES = [
    ("sci_volume", "Volume científico"),
    ("sci_growth", "Crescimento na ciência"),
    ("conf_volume", "Volume em congressos"),
    ("conf_growth", "Crescimento em congressos"),
    ("funding", "Chamadas internacionais"),
    ("media", "Mídia"),
    ("web", "Menções na web"),
    ("trends", "Google Trends"),
    ("mt_fit", "Aderência a Mato Grosso"),
]

ROTULO_CURTO = {
    "sci_volume": "Volume ciência", "sci_growth": "Cresc. ciência", "conf_volume": "Volume congressos",
    "conf_growth": "Cresc. congressos", "funding": "Chamadas int.", "media": "Mídia", "web": "Web",
    "trends": "Trends", "mt_fit": "Aderência MT",
}

RENOMEAR = {
    "Tema": "tema", "Score": "score", "Publicações (ano ref.)": "sci_vol", "Cresc. relativo ciência": "sci_cresc",
    "Trabalhos em congressos": "conf_vol", "Cresc. relativo congressos": "conf_cresc",
    "Chamadas int. abertas": "chamadas", "Mídia: intensidade": "midia_int", "Mídia: tendência": "midia_tend",
    "Menções web": "web", "Google Trends: tendência": "trends", "Aderência MT (1-5)": "mt_fit",
    "Sugestão de edital MT": "edital_mt",
}


# ---------------------------------------------------------------- execuções --
def pastas_base() -> list[Path]:
    bases = [RAIZ / "resultados"]
    extra = os.environ.get(ENV_DADOS)
    if extra:
        bases.append(Path(extra))
    return [b for b in bases if b.exists()]


def listar_execucoes() -> dict[str, Path]:
    """rótulo -> pasta, da execução mais recente para a mais antiga."""
    achadas: dict[str, Path] = {}
    for base in pastas_base():
        for d in base.iterdir():
            if d.is_dir() and (d / "prospeccao.xlsx").exists():
                achadas.setdefault(d.name, d)
    datas = sorted((k for k in achadas if re.fullmatch(r"\d{4}-\d{2}-\d{2}", k)), reverse=True)
    outras = sorted(k for k in achadas if k not in datas)
    return {k: achadas[k] for k in datas + outras}


@st.cache_data(show_spinner=False)
def _config(nome: str) -> dict:
    p = RAIZ / nome
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}


def config() -> dict:
    return _config("config.yaml")


def areas_cfg() -> dict:
    return _config("areas.yaml")


def radar_cfg() -> dict:
    return _config("radar.yaml")


@st.cache_data(show_spinner="Carregando execução…")
def _carregar(caminho: str, mtime: float) -> dict:  # noqa: ARG001  (mtime invalida o cache)
    pasta = Path(caminho)
    abas = pd.read_excel(pasta / "prospeccao.xlsx", sheet_name=None)
    dossie = None
    jf = pasta / "dados.json"
    if jf.exists():
        try:
            dossie = json.loads(jf.read_text(encoding="utf-8")).get("dossie")
        except (ValueError, OSError):
            dossie = None
    hist = pd.DataFrame()
    for candidato in (pasta.parent / "historico_scores.csv", pasta.parent / "historico.csv"):
        if candidato.exists():
            hist = pd.read_csv(candidato, encoding="utf-8-sig")
            break
    return {"abas": abas, "dossie": dossie, "hist": hist,
            "arquivos": {n: str(pasta / n) for n in ("prospeccao.xlsx", "relatorio.pdf", "relatorio.html")
                         if (pasta / n).exists()}}


class Execucao:
    """Visão de uma execução da prospecção, com os DataFrames já normalizados."""

    def __init__(self, rotulo: str, pasta: Path):
        self.rotulo, self.pasta = rotulo, pasta
        bruto = _carregar(str(pasta), (pasta / "prospeccao.xlsx").stat().st_mtime)
        self.abas: dict[str, pd.DataFrame] = bruto["abas"]
        self.dossie_json: dict | None = bruto["dossie"]
        self.hist: pd.DataFrame = bruto["hist"]
        self.arquivos: dict[str, str] = bruto["arquivos"]
        self.ranking = self._ranking()

    # --- helpers ---------------------------------------------------------
    def aba(self, nome: str) -> pd.DataFrame:
        return self.abas.get(nome, pd.DataFrame())

    @property
    def data(self) -> str:
        return self.rotulo

    def _ranking(self) -> pd.DataFrame:
        r = self.aba("Ranking").rename(columns=RENOMEAR).copy()
        if r.empty:
            return r
        r = r.sort_values("score", ascending=False).reset_index(drop=True)
        r.insert(0, "posicao", range(1, len(r) + 1))
        r["delta"] = r["id"].map(self._delta_por_id())
        return r

    def _delta_por_id(self) -> dict:
        h = self.hist
        if h.empty or "data" not in h:
            return {}
        anteriores = sorted(d for d in h["data"].unique() if d < self.rotulo)
        if not anteriores:
            return {}
        antes = h[h["data"] == anteriores[-1]].set_index("id")["score"]
        agora = self.ranking_scores_por_id()
        return {i: round(s - antes[i], 1) for i, s in agora.items() if i in antes.index}

    def ranking_scores_por_id(self) -> dict:
        r = self.aba("Ranking")
        return dict(zip(r["id"], r["Score"])) if not r.empty else {}

    @property
    def semana_anterior(self) -> str | None:
        h = self.hist
        if h.empty or "data" not in h:
            return None
        ant = sorted(d for d in h["data"].unique() if d < self.rotulo)
        return ant[-1] if ant else None

    # --- dossiê ----------------------------------------------------------
    @property
    def tem_dossie(self) -> bool:
        return not self.aba("Dossiê ICTs de MT").empty

    @property
    def tem_radar(self) -> bool:
        return not self.aba("Radar emergentes").empty

    def area_json(self, area_id: str) -> dict | None:
        return ((self.dossie_json or {}).get("areas") or {}).get(area_id)


def atual() -> Execucao:
    return st.session_state["execucao"]


def dias_ate(prazo) -> int | None:
    try:
        d = pd.to_datetime(prazo).date()
    except (ValueError, TypeError):
        return None
    return None if pd.isna(d) else (d - date.today()).days
