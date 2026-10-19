"""Scraping/RSS de páginas de congressos, órgãos de fomento e veículos científicos."""
from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .util import Http

log = logging.getLogger(__name__)


def _itens_html(http: Http, src: dict) -> list[dict]:
    if not http.allowed(src["url"]):
        log.warning("robots.txt bloqueia %s — ignorado", src["nome"])
        return []
    html = http.request("GET", src["url"], min_interval=2.0)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "noscript"]):
        tag.decompose()
    itens = []
    for el in soup.find_all(["h1", "h2", "h3", "h4", "a", "li", "p"]):
        txt = " ".join(el.get_text(" ", strip=True).split())
        if 25 <= len(txt) <= 300:
            href = urljoin(src["url"], el["href"]) if el.name == "a" and el.get("href") else src["url"]
            itens.append({"texto": txt, "url": href})
    return itens


def _itens_rss(http: Http, src: dict) -> list[dict]:
    xml = http.request("GET", src["url"], min_interval=1.0)
    if not xml:
        return []
    try:
        root = ET.fromstring(xml.encode("utf-8"))
    except ET.ParseError:
        log.warning("RSS inválido: %s", src["nome"])
        return []
    itens = []
    for it in root.iter():
        if it.tag.split("}")[-1] not in ("item", "entry"):
            continue
        g = {c.tag.split("}")[-1]: (c.text or "") for c in it}
        link = g.get("link") or next((c.get("href") for c in it if c.tag.endswith("link")), src["url"])
        desc = re.sub(r"<[^>]+>", " ", g.get("description") or g.get("summary") or "")
        itens.append({"texto": " ".join(f"{g.get('title', '')}. {desc}".split())[:400], "url": link})
    return itens


def _regex(termos: list[str]) -> list[re.Pattern]:
    """Siglas (CAR, SAF, ATER...) casam com diferenciação de maiúsculas; o resto ignora caixa."""
    termos = list(dict.fromkeys(termos))
    siglas = [k for k in termos if k.isupper() and len(k) <= 5]
    resto = [k for k in termos if k not in siglas]
    pats = []
    for lst, flags in ((resto, re.IGNORECASE), (siglas, 0)):
        if lst:
            pats.append(re.compile(r"(?<!\w)(" + "|".join(re.escape(k) for k in lst) + r")(?!\w)", flags))
    return pats


def coletar(http: Http, fontes: list[dict], temas: list[dict]) -> tuple[dict[str, dict], dict[str, int]]:
    regex = {t["id"]: _regex(t["keywords_en"] + t["keywords_pt"] + t.get("termos_amplos", [])) for t in temas}
    out = {t["id"]: {"mencoes": {}, "itens": []} for t in temas}
    status: dict[str, int] = {}
    for src in fontes:
        itens = _itens_rss(http, src) if src["type"] == "rss" else _itens_html(http, src)
        status[src["nome"]] = len(itens)
        vistos = set()
        for it in itens:
            if it["texto"] in vistos:
                continue
            vistos.add(it["texto"])
            for tid, rxs in regex.items():
                if any(rx.search(it["texto"]) for rx in rxs):
                    d = out[tid]
                    d["mencoes"][src["categoria"]] = d["mencoes"].get(src["categoria"], 0) + 1
                    d["itens"].append({"fonte": src["nome"], "categoria": src["categoria"], **it})
        log.info("Web     %-28s %4d itens lidos", src["nome"], len(itens))
    return out, status
