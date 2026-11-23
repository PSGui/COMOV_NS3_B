# P2 — Resultado estatístico dos 12 cenários (10 runs por cenário)

**Data:** 23/11/2026. **Fonte:** output fornecido pelo grupo após executar as 108 simulações adicionais (`run=2..10`) e chamar `scripts/paired_statistics_p2.py --output-dir out/p2 --start-run 1 --end-run 10`. As 12 simulações com run=1 já tinham sido verificadas. Total: **120 execuções** do ns-3.48, organizadas em **60 pares emparelhados**. O ficheiro `out/p2/paired_statistics.csv` está no computador do grupo, não foi enviado para auditoria independente neste passo.

## Resultados da diferença emparelhada FIFO − imediato

| Velocidade | Paragem | n pares | Diferença média na entrega / 12000 geradas | IC bilateral 95% (Student-t) |
|---:|---:|---:|---:|---:|
| 5 m/s | 0 s | 10 | +30,774 pp | [30,761; 30,787] pp |
| 5 m/s | 10 s | 10 | +30,774 pp | [30,761; 30,787] pp |
| 5 m/s | 30 s | 10 | +30,774 pp | [30,761; 30,787] pp |
| 15 m/s | 0 s | 10 | +33,325 pp | [33,319; 33,331] pp |
| 15 m/s | 10 s | 10 | +33,325 pp | [33,319; 33,331] pp |
| 15 m/s | 30 s | 10 | +33,325 pp | [33,319; 33,331] pp |

**Definição do estimador:**

```
P_on_time(policy, run) = N_unique_received_on_time(policy, run) / 12000
D(run) = 100 × (P_on_time(FIFO, run) − P_on_time(immediate, run))  [pontos percentuais]
D_mean = mean(D(run=1..10))
IC95% = D_mean ± t_0.975,9 × stdev_sample(D) / sqrt(10)
t_0.975,9 ≈ 2.262
```

A tabela representa **diferenças emparelhadas por seed/run e cenário**, não a diferença de percentagens estimadas em amostras independentes. As conclusões referem-se ao código, parâmetros e configuração de propagação atuais.

## Auditoria do ficheiro agregado recebido

Ficheiro analisado diretamente: `paired_statistics.csv`, recebido a 23/11/2026. SHA-256: `27ba59669fb61a0fa8712e1446e308c57e601ffcd763d3a3eb2b7dd8adf67df1`. Contém **6 linhas de cenários e 13 colunas**, incluindo taxas médias das duas políticas, diferença emparelhada, limites IC95% e médias de descarte/ocupação. Não contém os valores individuais das dez runs. A integridade aritmética foi verificada: taxa FIFO menos taxa imediata coincide com diferença reportada, e a média do acréscimo de mensagens corresponde à diferença em pontos percentuais multiplicada por 120.

### Médias exatas por política obtidas do CSV (n=10 pares por condição)

| v m/s | Paragem s | Taxa imediata média | Taxa FIFO média | Ganho (pp) | Média de mensagens adicionais |
|---:|---:|---:|---:|---:|---:|
| 5 | 0 | 38,5092% | 69,2833% | +30,7742 | +3692,9 |
| 5 | 10 | 46,8425% | 77,6167% | +30,7742 | +3692,9 |
| 5 | 30 | 63,5092% | 94,2833% | +30,7742 | +3692,9 |
| 15 | 0 | 12,8042% | 46,1292% | +33,3250 | +3999,0 |
| 15 | 10 | 21,1375% | 54,4625% | +33,3250 | +3999,0 |
| 15 | 30 | 37,8042% | 71,1292% | +33,3250 | +3999,0 |

### Média de perdas de aplicação e ocupação FIFO, por simulação

| v m/s | Paragem s | Overflow `drop-newest` | Expiradas antes de envio | Ocupação de pico média |
|---:|---:|---:|---:|---:|
| 5 | 0 | 0,0 | 3588,1 | 3,6939 MB |
| 5 | 10 | 0,0 | 2585,2 | 3,6939 MB |
| 5 | 30 | 0,0 | 587,8 | 3,6939 MB |
| 15 | 0 | 2366,6 | 4000,0 | 4,0000 MB |
| 15 | 10 | 1366,4 | 4000,0 | 4,0000 MB |
| 15 | 30 | 1235,5 | 2130,9 | 4,0000 MB |

**Interpretação:** maior paragem aumenta a média de entregas nas duas políticas, e reduz as expirações na FIFO. A maior velocidade esgota os 4 MB de capacidade em todos os casos estudados. Os intervalos de confiança disponibilizados são apenas para a **diferença emparelhada FIFO−imediato**; não devem ser desenhados como margens de erro das taxas individuais. A partir de um CSV agregado, não é possível recalcular independentemente o desvio-padrão das dez diferenças nem todos os percentis de atraso.

## O que está realmente demonstrado

1. O código ns-3 completou as 120 simulações no conjunto de configurações experimentais declarado, com validação automática por cenário e par. O log de conclusão das últimas 108 execuções reportou `108 newly executed, 0 reused; 54 pairs`.
2. Sob as hipóteses adotadas, a política FIFO aumenta a fração de mensagens entregues dentro dos 60 segundos, com ganho médio aproximado de **30,77 pp a 5 m/s** e **33,33 pp a 15 m/s**.
3. Os intervalos de confiança emparelhados não abrangem zero e são muito estreitos **dentro da variabilidade do simulador**, mas isso não estabelece validade externa da estimativa para um ambiente rodoviário.
4. O ganho médio da FIFO é numericamente igual para as paragens 0/10/30 s em cada velocidade. Isto é consistente com a fila recuperar as mensagens **pré-associação**, cujo número depende sobretudo da velocidade de aproximação e da capacidade de 4 MB. A paragem altera o tempo útil de contacto e os totais de entrega das duas políticas, como já visto na matriz run=1.
5. O custo em atraso continua relevante: os primeiros pilotos observaram atraso médio FIFO de segundos/dezenas de segundos, em oposição ao atraso de milissegundos no envio imediato. O resumo de médias de atraso em todas as 10 runs **não foi calculado pelo script atual**, portanto não se deve extrapolar valores de run=1 como médias estatísticas.

## Limitações — importantes para a defesa

- **Canal determinístico:** modelo log-distance sem shadowing variável, fading, obstáculos nem tráfego concorrente. Os ICs estreitos refletem apenas a aleatoriedade interna simulada (incluindo MAC, consoante as configurações); não a variabilidade de uma estrada real.
- **Independência e streams RNG:** os pares usam o mesmo seed e número de run, mas deve confirmar-se se streams aleatórios foram atribuídos de modo explícito. Usar seed/run iguais *não garante* que cada entidade consuma a mesma sequência RNG nas duas políticas.
- **Repetições:** são n=10 pares por cada uma das seis combinações físicas, não 60 repetições de uma única condição.
- **Pacing:** FIFO de 4 MB, `drop-newest`, limite de 60 s e espaçamento nominal 2 ms foram parâmetros definidos antes da matriz. O teste de 3 ms foi exploratório; não prova o ótimo de pacing.
- **Mecanismos de perda:** `SendTo` devolvendo 1000 bytes significa aceitação pelo socket UDP, não entrega; as mensagens aceites mas não observadas não foram diagnosticadas com traces PHY/MAC.
- **Resumo estatístico:** sem os CSV das 10 runs nesta interação, apenas os ICs e médias impressos pelo script estão disponíveis; a auditoria externa detalhada da distribuição é futura.

## Análise recomendada antes de fechar relatório

1. Inspecionar e conservar `out/p2/paired_statistics.csv`; confirmar as médias de entrega das **duas** políticas, contagens médias de overflow e expiração, além da diferença.
2. Criar duas figuras de leitura direta: taxas médias de entrega imediato/FIFO com IC95% adequados à grandeza representada, e diferenças emparelhadas por velocidade/paragem. O IC95% atualmente disponível pertence à **diferença**, não deve ser desenhado indevidamente sobre cada taxa isolada.
3. Calcular por cenário a distribuição de atrasos (média, P95, máximo) sobre as mensagens entregues nas 10 runs, deixando claro que os atrasos dos descartes não são observados.
4. Se houver interesse em generalização para uma estrada, efetuar ensaios de **robustez de propagação** (por exemplo, expoentes alternativos e shadowing/fading bem parametrizados), separando-os da matriz de referência. Não misturar resultados dos novos modelos no mesmo IC.
5. Preparar texto do relatório: hipóteses, definições de métricas e denominadores, comparação entre políticas, impacto da paragem e capacidade, limitações e conclusões.

## Estado do trabalho e comando para a tabela estatística

A matriz, as repetições e os IC95% **estão concluídos para a configuração de referência**. Falta transformar os resultados em figuras, auditar os CSV agregados e redigir a análise/limitações. A mensagem genérica `Do not calculate IC95% from only one run per scenario` surge no fim do script da matriz e refere-se apenas ao caso de n=1; a etapa posterior correu corretamente com n=10.

Para inspecionar o ficheiro agregado sem repetir nenhuma simulação:

```bash
python3 - <<'PY'
import csv
with open("out/p2/paired_statistics.csv", newline="") as f:
    for row in csv.DictReader(f):
        print(row)
PY
```

Ver também [matriz inicial run=1](15_resultados_matriz_12_cenarios_run1.md).
