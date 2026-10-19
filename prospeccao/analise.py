"""Combina os sinais de cada fonte em um score 0-100 por tema."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _g(d: dict | None, tid: str, *path):
    cur = (d or {}).get(tid)
    for p in path:
        if cur is None:
            return None
        cur = cur.get(p) if isinstance(cur, dict) else None
    return cur


def calcular(temas: list[dict], pesos: dict, ciencia, editais, midia, web, trends=None) -> pd.DataFrame:
    rows = []
    for t in temas:
        i = t["id"]
        n_edital = _g(editais, i, "n")
        mencoes = _g(web, i, "mencoes")
        trend = _g(midia, i, "tendencia")
        intens = _g(midia, i, "intensidade")
        rows.append({
            "id": i, "tema": t["nome"],
            "sci_volume": _g(ciencia, i, "sci_volume"),
            "sci_growth": _g(ciencia, i, "sci_growth"),
            "conf_volume": _g(ciencia, i, "conf_volume"),
            "conf_growth": _g(ciencia, i, "conf_growth"),
            "funding": n_edital,
            "media_intensidade": intens, "media_tendencia": trend,
            "web": sum(mencoes.values()) if mencoes is not None else None,
            "trends": _g(trends, i, "tendencia"),
            "mt_fit": t["mt_fit"],
        })
    df = pd.DataFrame(rows).set_index("id")

    # Métrica de mídia: média dos percentis de intensidade e tendência
    pct = lambda s: s.rank(pct=True) * 100  # noqa: E731
    p = pd.DataFrame(index=df.index)
    for col in ("sci_volume", "conf_volume", "funding", "web"):
        p[col] = pct(df[col].astype(float).map(lambda v: math.log1p(v) if pd.notna(v) else np.nan))
    for col in ("sci_growth", "conf_growth", "trends"):
        p[col] = pct(df[col].astype(float))
    p["media"] = pd.concat([pct(df["media_intensidade"].astype(float)),
                            pct(df["media_tendencia"].astype(float))], axis=1).mean(axis=1, skipna=False)
    p["mt_fit"] = (df["mt_fit"].astype(float) - 1) / 4 * 100

    w = pd.Series(pesos)
    ok = p[w.index].notna()
    peso_ef = ok.mul(w, axis=1)
    df["score"] = (p[w.index].fillna(0).mul(w, axis=1).sum(axis=1) / peso_ef.sum(axis=1)).round(1)
    for c in p.columns:
        df[f"p_{c}"] = p[c].round(0)
    return df.sort_values("score", ascending=False)
