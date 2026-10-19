# Radar de tecnologias emergentes

Segunda lista do relatório, com critério oposto ao do ranking de temas: favorece tecnologias com **pouco volume e
crescimento alto** (estágio inicial), em vez de assuntos já consolidados. Configuração em `radar.yaml`
(tecnologias, termos de busca e pesos).

## Fontes (todas verificadas)

| Sinal | Fonte | O que mede |
|---|---|---|
| Pesquisa | OpenAlex (`type:preprint`) e arXiv | preprints no último semestre vs. o anterior |
| Código aberto | GitHub (busca de repositórios) | repositórios criados nos últimos 12 meses vs. os 12 anteriores |
| IA aplicada | Hugging Face | modelos e datasets criados nos últimos 90 dias |
| Startups | Y Combinator (API) e AgFunder News (RSS) | empresas das últimas turmas e menções em notícias |
| Pesquisa financiada | Horizon Europe | chamadas abertas do tipo *Research and Innovation Actions*/EIC (aproximação de TRL baixo) |

## Score e estágio

Score 0–100 = média ponderada de percentis (pesos em `radar.yaml`). **Imaturidade** soma pontos para menor volume total
de publicações. **Estágio**: *Nascente* (volume baixo, crescimento alto), *Em aceleração* (crescimento alto, volume
relevante), *Incipiente* (volume baixo, sem tração), *Estabelecida*.

## Limites

* Contagens pequenas oscilam muito — o crescimento é suavizado, mas leia os exemplos listados antes de decidir.
* As buscas são em inglês e por frase; vocabulário diferente fica subestimado. Ajuste `kw` em `radar.yaml`.
* Não há TRL real: a API do Horizon não expõe o campo, então o tipo de ação é só uma aproximação.
* GitHub sem token limita a 10 buscas/min (a coleta fica lenta); no Actions o `GITHUB_TOKEN` já é repassado.
* Com `--temas`, o radar é pulado (teste rápido); use `--radar-tudo` para rodá-lo mesmo assim.
