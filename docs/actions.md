# Execução automática (GitHub Actions)

O workflow `.github/workflows/prospeccao.yml` roda **toda segunda, 06:00 em Cuiabá**, e também sob demanda
(aba **Actions → Prospecção de tendências → Run workflow**; dá para limitar a alguns temas).

Configuração única, em **Settings → Secrets and variables → Actions**:

* **Secret** `OPENALEX_API_KEY` — a chave gratuita do OpenAlex.
* **Variable** (opcional) `OPENALEX_MAILTO` — seu e-mail, para o "polite pool" do OpenAlex.

A cada execução:

* os resultados são commitados em `resultados/AAAA-MM-DD/` (`relatorio.html`, `prospeccao.xlsx`) e o
  `resultados/historico_scores.csv` acumula a evolução semanal dos scores;
* os arquivos completos (inclusive `dados.json`) ficam como *artifact* por 90 dias;
* o `.cache/` é preservado entre execuções, então o Google Trends completa os temas que faltaram ao longo das semanas;
* o GDELT é pulado (IPs de runners costumam receber 429) e o Google News assume a mídia.

Falhas de uma fonte não derrubam o job: o relatório sai sem aquele sinal e os pesos se redistribuem.

## Envio do relatório por e-mail (opcional)

Ao final de cada execução, `enviar_email.py` manda o ranking (corpo) + `relatorio.html` e `prospeccao.xlsx` (anexos).
Sem as credenciais abaixo o passo é ignorado e o job segue normalmente.

Em **Settings → Secrets and variables → Actions → Secrets**:

| Secret | Valor |
|---|---|
| `SMTP_USER` | e-mail remetente (ex.: sua conta Gmail) |
| `SMTP_PASSWORD` | **senha de app**, não a senha da conta (Gmail: Conta Google → Segurança → Verificação em duas etapas → Senhas de app) |
| `EMAIL_TO` | destinatários separados por vírgula |

Opcionais (em **Variables**): `SMTP_HOST` (padrão `smtp.gmail.com`) e `SMTP_PORT` (padrão `465`/SSL; para Microsoft 365 use
`smtp.office365.com` e `587`, que usa STARTTLS — pode exigir SMTP autenticado habilitado pelo administrador do tenant).

Teste local sem enviar: `python enviar_email.py AAAA-MM-DD --dry-run` (grava um `.eml`).

