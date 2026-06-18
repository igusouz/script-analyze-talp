# TALP Multi-Agent Quantitative Analyzer

Script Python para analise quantitativa de resultados da plataforma TALP Multi-Agent.

## Requisitos

- Python 3.11+
- Dependencias em `requirements.txt`

## Instalação

```bash
python -m pip install -r requirements.txt
```

## Estrutura

- `analyzer/parser.py`: leitura e normalizacao dos JSONs.
- `analyzer/metrics.py`: metricas INVEST, Compliance, BDD, Cobertura e Robustez.
- `analyzer/hallucination.py`: heuristicas deterministicas de possivel alucinacao.
- `analyzer/ranking.py`: classificacao final e ranking.
- `analyzer/agent_report.py`: avaliacao consolidada por agente (INVEST, Compliance e BDD).
- `analyzer/metric_report.py`: avaliacao estatistica por metrica e recomendacao de uso.
- `analyzer/bdd_applicability.py`: avaliacao de aplicabilidade dos cenarios BDD em relacao aos criterios de aceite.
- `analyzer/exporter.py`: exportacao de `summary.csv`, `statistics.csv`, `agent_report.csv`, `metric_report.csv` e relatorios individuais por agente.
- `analyzer/individual_reports.py`: analise individual das saidas de INVEST, Compliance e BDD por arquivo.
- `analyzer/main.py`: pipeline principal e CLI.

## Execução

```bash
python -m analyzer.main --input-dir ./input --output-dir ./output
```

Observacao: se `--output-dir` nao for informado, o padrao da CLI e `./outputs`.

## Testes

```bash
pytest -q
```

## Arquivos gerados

- `summary.csv`: resultado consolidado por arquivo de entrada.
- `statistics.csv`: medias agregadas do lote.
- `agent_report.csv`: score por agente do fluxo.
- `metric_report.csv`: relevancia/recomendacao por metrica.
- `invest_individual_report.csv`: analise individual da saida do agente INVEST por arquivo.
- `compliance_individual_report.csv`: analise individual da saida do agente Compliance por arquivo.
- `bdd_individual_report.csv`: analise individual da saida do agente BDD por arquivo.
	- inclui score de aplicabilidade dos cenarios BDD (`bdd_applicability_score`) com cobertura de criterios de aceite.

## Campos principais em summary.csv

- arquivo
- tipo_us
- invest_score
- compliance_score
- bdd_scenarios
- edge_cases
- ambiguidades
- riscos
- hallucination_score
- robustness_score
- classificacao
- ranking
- invest_aprovados
- invest_reprovados
- invest_criterios_reprovados
- invest_status
- compliance_total_regras
- compliance_obrigatorias_satisfeitas
- compliance_gaps
- compliance_status
- bdd_positive
- bdd_negative
- refinement_questions
- automation_suggestions
- bdd_applicability_score
- bdd_applicability_level
- bdd_ac_coverage
- bdd_ac_covered
- bdd_ac_total
- bdd_applicable_scenarios
- bdd_applicability_reasons
- coverage
- coverage_normalized
- hallucination_level
- hallucination_reasons

## Ordenacao de ranking

1. `robustness_score` (desc)
2. `compliance_score` (desc)
3. `invest_score` (desc)
4. `hallucination_score` (asc)
