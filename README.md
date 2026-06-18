# TALP Multi-Agent Quantitative Analyzer

Script Python para análise quantitativa de resultados da plataforma TALP Multi-Agent.

## Requisitos

- Python 3.11+
- Dependências em `requirements.txt`

## Instalação

```bash
python -m pip install -r requirements.txt
```

## Estrutura

- `analyzer/parser.py`: leitura e normalizacao dos JSONs.
- `analyzer/metrics.py`: métricas INVEST, Compliance, BDD, Cobertura e Robustez.
- `analyzer/hallucination.py`: heurísticas determinísticas de possível alucinação.
- `analyzer/ranking.py`: classificação final e ranking.
- `analyzer/agent_report.py`: avaliação consolidada por agente (INVEST, Compliance e BDD).
- `analyzer/metric_report.py`: avaliação estatística por métrica e recomendação de uso.
- `analyzer/bdd_applicability.py`: avaliação de aplicabilidade dos cenários BDD em relação aos critérios de aceite.
- `analyzer/exporter.py`: exportação de `summary.csv`, `statistics.csv`, `agent_report.csv`, `metric_report.csv` e relatórios individuais por agente.
- `analyzer/individual_reports.py`: análise individual das saídas de INVEST, Compliance e BDD por arquivo.
- `analyzer/main.py`: pipeline principal e CLI.

## Execução

```bash
python -m analyzer.main --input-dir ./input --output-dir ./output
```

Observação: se `--output-dir` não for informado, o padrão da CLI é `./outputs`.

## Testes

```bash
pytest -q
```

## Arquivos gerados

- `summary.csv`: resultado consolidado por arquivo de entrada.
- `statistics.csv`: médias agregadas do lote.
- `agent_report.csv`: score por agente do fluxo.
- `metric_report.csv`: relevância/recomendação por métrica.
- `invest_individual_report.csv`: análise individual da saída do agente INVEST por arquivo.
- `compliance_individual_report.csv`: análise individual da saída do agente Compliance por arquivo.
- `bdd_individual_report.csv`: análise individual da saída do agente BDD por arquivo.
  - Inclui score de aplicabilidade dos cenários BDD (`bdd_applicability_score`) com cobertura de critérios de aceite.

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

## Ordenação de ranking

1. `robustness_score` (desc)
2. `compliance_score` (desc)
3. `invest_score` (desc)
4. `hallucination_score` (asc)
