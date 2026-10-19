"""HTML -> PDF imprimindo com Chrome/Chromium/Edge em modo headless (sem dependências Python)."""
from __future__ import annotations

import logging
import os
import pathlib
import shutil
import subprocess
import tempfile

log = logging.getLogger(__name__)

_NOMES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge")
_CAMINHOS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)


def achar_navegador() -> str | None:
    if os.getenv("CHROME_BIN"):
        return os.environ["CHROME_BIN"]
    for n in _NOMES:
        if (p := shutil.which(n)):
            return p
    return next((p for p in _CAMINHOS if pathlib.Path(p).exists()), None)


def html_para_pdf(html: pathlib.Path, pdf: pathlib.Path, timeout: int = 120) -> bool:
    """Gera o PDF; devolve False (sem levantar) se não houver navegador ou a impressão falhar."""
    nav = achar_navegador()
    if not nav:
        log.warning("Nenhum Chrome/Edge encontrado — PDF não gerado (defina CHROME_BIN para indicar o caminho)")
        return False
    pdf.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory() as perfil:   # perfil isolado: não interfere no navegador aberto do usuário
        cmd = [nav, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run",
               f"--user-data-dir={perfil}", "--no-pdf-header-footer", "--virtual-time-budget=5000",
               f"--print-to-pdf={pdf.resolve()}", html.resolve().as_uri()]
        try:
            subprocess.run(cmd, check=False, timeout=timeout, capture_output=True)
        except (subprocess.TimeoutExpired, OSError) as e:
            log.warning("Falha ao imprimir o PDF: %s", e)
            return False
    ok = pdf.exists() and pdf.stat().st_size > 1000
    if not ok:
        log.warning("O navegador não produziu o PDF (%s)", nav)
    return ok
