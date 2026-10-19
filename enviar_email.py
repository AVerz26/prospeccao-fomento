"""Envia o relatório por e-mail (SMTP). Uso: python enviar_email.py AAAA-MM-DD [--dry-run]

Variáveis de ambiente:
  EMAIL_TO        destinatários separados por vírgula (obrigatória)
  SMTP_USER       usuário/remetente (obrigatória)
  SMTP_PASSWORD   senha de app (obrigatória)
  SMTP_HOST       padrão smtp.gmail.com
  SMTP_PORT       padrão 465 (SSL); qualquer outra porta usa STARTTLS (ex.: 587)
  EMAIL_FROM      padrão = SMTP_USER

Se faltar EMAIL_TO, SMTP_USER ou SMTP_PASSWORD, o envio é ignorado sem erro.
--dry-run grava a mensagem em .eml em vez de enviar.
"""
from __future__ import annotations

import csv
import html
import os
import pathlib
import smtplib
import ssl
import sys
from email.message import EmailMessage

ROOT = pathlib.Path(__file__).resolve().parent


def ranking(dia: str, n: int = 10) -> list[tuple[str, float]]:
    for f in (ROOT / "output" / "historico_scores.csv", ROOT / "resultados" / "historico_scores.csv"):
        if f.exists():
            with f.open(encoding="utf-8-sig") as fh:
                linhas = [r for r in csv.DictReader(fh) if r["data"] == dia]
            return sorted(((r["tema"], float(r["score"])) for r in linhas), key=lambda x: -x[1])[:n]
    return []


def montar(dia: str, destinatarios: list[str], remetente: str) -> EmailMessage:
    pasta = ROOT / "output" / dia
    top = ranking(dia)
    msg = EmailMessage()
    msg["Subject"] = f"Prospecção de tendências para editais (MT) — {dia}"
    msg["From"], msg["To"] = remetente, ", ".join(destinatarios)

    txt = [f"Prospecção de tendências — {dia}", "", "Top temas por score (0-100):"]
    txt += [f"{i}. {t} — {s:.0f}" for i, (t, s) in enumerate(top, 1)]
    txt += ["", "Relatório completo (HTML) e planilha em anexo."]
    msg.set_content("\n".join(txt))

    linhas = "".join(f"<tr><td>{i}</td><td>{html.escape(t)}</td><td><b>{s:.0f}</b></td></tr>"
                     for i, (t, s) in enumerate(top, 1))
    msg.add_alternative(
        f"<h2>Prospecção de tendências para editais (MT)</h2><p>Execução de {dia}.</p>"
        f"<table cellpadding=6 style='border-collapse:collapse'><tr><th>#</th><th>Tema</th><th>Score</th></tr>{linhas}</table>"
        "<p>O relatório completo (HTML) e a planilha seguem em anexo. O score é relativo aos temas "
        "monitorados — veja a metodologia no relatório.</p>", subtype="html")

    for nome, mime in (("relatorio.html", ("text", "html")), ("prospeccao.xlsx", (
            "application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet"))):
        f = pasta / nome
        if f.exists():
            msg.add_attachment(f.read_bytes(), maintype=mime[0], subtype=mime[1], filename=f"{dia}-{nome}")
    return msg


def main() -> int:
    dia = next((a for a in sys.argv[1:] if not a.startswith("--")), None)
    if not dia:
        print(__doc__)
        return 2
    dry = "--dry-run" in sys.argv
    user, senha = os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASSWORD", "")
    dest = [e.strip() for e in os.getenv("EMAIL_TO", "").split(",") if e.strip()]
    if not dry and not (user and senha and dest):
        print("E-mail não configurado (EMAIL_TO / SMTP_USER / SMTP_PASSWORD) — envio ignorado.")
        return 0

    msg = montar(dia, dest or ["destino@exemplo.com"], os.getenv("EMAIL_FROM") or user or "remetente@exemplo.com")
    if dry:
        out = ROOT / f"email-{dia}.eml"
        out.write_bytes(bytes(msg))
        print(f"Mensagem gravada em {out} ({out.stat().st_size // 1024} KB)")
        return 0

    host, porta = os.getenv("SMTP_HOST", "smtp.gmail.com"), int(os.getenv("SMTP_PORT", "465"))
    ctx = ssl.create_default_context()
    if porta == 465:
        with smtplib.SMTP_SSL(host, porta, context=ctx, timeout=60) as s:
            s.login(user, senha)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, porta, timeout=60) as s:
            s.starttls(context=ctx)
            s.login(user, senha)
            s.send_message(msg)
    print(f"E-mail enviado para {len(dest)} destinatário(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
