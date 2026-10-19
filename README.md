# Prospecção de tendências para editais de fomento (Mato Grosso)

Coleta sinais de várias fontes abertas sobre o que está em alta no mundo, pontua cada tema e gera
um relatório (HTML + Excel) com **ranking de temas**, **chamadas internacionais de referência** e uma
**sugestão de linha de edital** adequada a MT.

## Como funciona

| Sinal | Fonte | Como |
|---|---|---|
| Ciência e congressos | OpenAlex (API) | publicações por tema, crescimento da participação no corpus e trabalhos em anais de congressos |
| Fomento internacional | Horizon Europe (EU Funding & Tenders) e Grants.gov (EUA) | chamadas abertas/previstas por tema |
| Mídia global | GDELT (API); se falhar, Google News (RSS) | volume e tendência 30d vs 30d anteriores, manchetes recentes |
| Buscas | Google Trends (pytrends, não oficial) | tendência de 12 meses e consultas relacionadas em alta (as "chaves de pesquisa" do momento) |
| Congressos, fomento BR, ciência | scraping + RSS (`fontes_web` no `config.yaml`) | menções dos temas, respeitando `robots.txt` |
| Aderência a MT | campo `mt_fit` (1–5) em cada tema | julgamento seu; é o que ancora o ranking na realidade do estado |

Score 0–100 = média ponderada dos percentis dos sinais (pesos em `config.yaml`).

## Uso

```bash
pip install -r requirements.txt
python run.py                       # tudo (≈10–15 min; o GDELT exige intervalo entre chamadas)
python run.py --skip midia          # pula uma fonte
python run.py --temas bioinsumos    # só alguns temas (teste)
python run.py --no-cache            # ignora o cache de 12 h (.cache/)
```

Saídas em `output/AAAA-MM-DD/`: `relatorio.html`, `prospeccao.xlsx`, `dados.json`.
`output/historico_scores.csv` acumula o score de cada execução para você ver a evolução.

## Recomendado: chave gratuita do OpenAlex

Sem chave, o limite diário é pequeno e compartilhado pelo seu IP. Crie uma em https://openalex.org/settings/api e:

```powershell
$env:OPENALEX_API_KEY = "sua-chave"
$env:OPENALEX_MAILTO  = "seu@email"
```

## Personalizar

* **Temas**: edite `temas` em `config.yaml` (palavras-chave EN para fontes internacionais, PT para páginas brasileiras).
* **Fontes**: acrescente páginas de congressos ou órgãos em `fontes_web`. Páginas que carregam conteúdo por JavaScript
  (ex.: sites de eventos feitos em SPA) não funcionam com este scraper — prefira RSS ou procure uma API.
* **Pesos**: ajuste `pesos` conforme a estratégia (ex.: aumentar `funding` se o foco é captar recursos).

## Limites conhecidos

* FAPEMAT bloqueia robôs via `robots.txt` — acompanhe manualmente ou peça um feed ao órgão.
* GDELT cobre notícias em inglês e limita requisições (429); nesse caso o Google News RSS assume para todos os temas. O RSS devolve no máximo ~100 itens, então temas muito quentes saturam e a tendência fica em 0%.
* Google Trends também limita (429). Os resultados ficam em cache por 7 dias (`.cache/trends.json`); rode de novo para completar os temas que faltaram. Não fazemos scraping da busca do Google (viola os termos e é bloqueada).
* A busca de editais internacionais é filtrada por relevância (todos os termos de uma palavra-chave devem aparecer no título): poucos resultados por tema é esperado.
* O ranking é **relativo** aos temas listados. Um tema fora da lista não aparece.
* Palavras-chave medem *menção*, não *importância*. Use o relatório para priorizar a leitura, não para decidir sozinho.

## Agendar execução semanal (Windows)

```powershell
schtasks /Create /SC WEEKLY /D MON /ST 07:00 /TN "ProspeccaoFomentoMT" /TR "python \"%CD%\run.py\""
```
