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
