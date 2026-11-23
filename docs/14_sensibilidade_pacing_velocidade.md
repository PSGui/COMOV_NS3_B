# P2 — Sensibilidade ao pacing e à velocidade (21 CSV auditados)

**Data:** 23/11/2026. **Origem:** ZIP do grupo, com 21 CSV reais de três simulações ns-3.48. Execuções individuais com seed=1/run=1; não existe IC95% nestes ensaios. SHA-256 do ZIP original: 456d170c663749b28e587aaff92ddafcc17093e36727056f2240a10f268cfec1.

## Resultados consolidados

| Cenário | Aceites UDP | Entregues <=60 s / 12000 | Taxa entrega | Aceites mas não observadas |
|---|---:|---:|---:|---:|
| 5 m/s, imediato | 5720 | 5620 | 46,8333% | 100 |
| 5 m/s, FIFO 2 ms | 9415 | 9312 | 77,6000% | 103 |
| **5 m/s, FIFO 3 ms** | 9415 | **9314** | **77,6167%** | 101 |
| **15 m/s, imediato** | 2629 | **2533** | **21,1083%** | 96 |
| **15 m/s, FIFO 2 ms** | 6629 | **6530** | **54,4167%** | 99 |

Na velocidade 15 m/s, o FIFO recupera **3997 mensagens** (+33,3083 pontos percentuais), comparado com envio imediato. A 5 m/s, mudar o pacing de 2 ms para 3 ms aumenta apenas **2 mensagens** (+0,0167 pontos percentuais), com aumento de atraso. Não selecionar 3 ms com base nesta diferença de uma run.

## Atraso das mensagens efetivamente recebidas

| Cenário | Média | P95 | Máximo |
|---|---:|---:|---:|
| 5 m/s FIFO, 2 ms | 9,151 s | 33,194 s | 36,952 s |
| 5 m/s FIFO, 3 ms | 10,465 s | 33,676 s | 36,952 s |
| 15 m/s imediato | 1,488 ms | 1,478 ms | 11,704 ms |
| 15 m/s FIFO, 2 ms | 22,881 s | 49,752 s | 52,398 s |

Os valores referem-se apenas a mensagens recebidas no AP. A FIFO de 3 ms esvazia pela primeira vez em t=**62,768679 s**, comparado com t=**56,174679 s** a 2 ms: mais 6,594 s para consumir o backlog inicial. A **15 m/s e 2 ms**, esvazia em t=**72,384112 s**, já com o autocarro parado (paragem de t=70 a 80 s).

## Cronologia rigorosa do caso 15 m/s, 10 s, FIFO 2 ms

| Evento | Tempo (s) | Evidência |
|---|---:|---|
| Começo da geração | 10,000 | 100 mensagens/s |
| Fila atinge 4 MB | 49,990 | 4000 mensagens |
| Primeiro overflow drop-newest | 50,000 | ID 4000 |
| **Associação Wi-Fi** | **62,386111762** | x=-114,208 m; d3d≈114,218 m |
| Primeiro envio FIFO | 62,386111762 | ID 0, gerado em t=10 s |
| Começo da paragem | 70,000 | x=0 |
| Primeira vez sem backlog | **72,384111762** | durante a paragem |
| Fim da paragem | 80,000 | velocidade volta a 15 m/s |
| Última receção UDP | 87,711478 | ID 7771 |
| **Desassociação Wi-Fi** | **88,678376383** | x≈130,176 m; d3d≈130,184 m |
| Primeira expiração pós-contacto | 148,680 | ID 7868 |
| Última expiração pós-contacto | 188,670 | ID 11867 |

Duração de associação: **26,292265 s** a 15 m/s, comparado com **57,200098 s** a 5 m/s.

### Dois períodos de overflow distintos

- **Antes da associação:** fila cheia em t=49,99 s, ainda faltavam ~12,40 s para associar. Descartados **1239 IDs consecutivos 4000–5238**, gerados em [50,00; 62,38] s.
- **Depois da desassociação:** fila acumula **4000 IDs 7868–11867** entre [88,68; 128,67] s, sem nova associação, e descarta **132 IDs 11868–11999** entre [128,68; 129,99] s. Todos os 4000 enfileirados após a desassociação expiram aos 60 s de idade (148,68–188,67 s).

Conservação exata: **12000 = 10629 enfileiradas + 1371 overflow (1239+132)**. **10629 = 6629 enviadas/aceites UDP + 4000 expiradas**. **6629 = 6530 entregues + 99 aceites não observadas no AP**. Ocupação máxima = 4000000 B; nenhuma mensagem pendente no final.

### Identificadores entregues e não observados

- Antes da associação, geraram-se **5239 mensagens IDs 0–5238**. A FIFO armazenou os **4000 primeiros IDs 0–3999** e o AP recebeu **3997** (não observou IDs 3–5).
- Durante a associação, ambas as políticas entregaram **2533 mensagens IDs 5239–7771**.
- Datagramas aceites e não observados: **imediato IDs 7772–7867 (96 mensagens)**; **FIFO IDs 3–5 e 7772–7867 (99)**.
- FIFO 3 ms a 5 m/s: não observados **ID 3**, mais **IDs 9315–9414 (100)**.

Não atribuir as não receções a causas PHY/MAC específicas sem traces. Estar associado não é prova de entrega. O corte final coincide com perda de receções perto do limite nominal de deteção de preâmbulo do ns-3.48, mas uma relação causal exige instrumentação.

## Interpretação e próximos controlos

- **Pacing:** 2 ms continua como baseline provisória. A 3 ms, o atraso médio foi maior em 1,314 s e o ganho de 2 mensagens é desprezível face à variação ainda não estudada entre runs.
- **Buffer:** a 15 m/s, os 4 MB não chegam para armazenar todos os dados pré-associação; a capacidade deve ser tratada como uma variável com justificação, não como ausência de overflow garantida.
- **Paragem:** a 5 m/s o backlog esvaziou antes de t=70 s, mas a 15 m/s só durante a paragem. A importância causal da duração da paragem será avaliada em 0/10/30 s, não inferida deste único caso.
- **Prazo:** a primeira mensagem enviada a 15 m/s tinha idade 52,386 s e chegou com atraso 52,398 s, ainda dentro dos 60 s, mas com margem reduzida.
- **Inferência:** resultados de run=1 são pilotos. Fazer os **seis pares** (2 velocidades ×3 paragens), inicialmente uma run; depois ≥10 runs emparelhadas por par, com IC95% das diferenças e controlo das fontes de aleatoriedade. IC estreitos num canal determinístico não demonstram realismo de uma estrada.

## Proveniência dos CSV

ZIP original (21 CSV): SHA-256 **456d170c663749b28e587aaff92ddafcc17093e36727056f2240a10f268cfec1**.

Hashes SHA-256 internos:
- v15_stop10_run1_immediate_summary.csv: 67053ea259ce6cfbe313cf47ce5eabc4c8e954bdd1fd9d0075ddf59af42de08d
- v15_stop10_run1_fifo_summary.csv: 9e735551e42c8415ca8329716949fbc9af7bb0d86c0ceef802ab961a27e5430d
- v15_stop10_run1_fifo_buffer.csv: 0b157e3bd6dab29ca5fd96e1c93ccbad1d33f1ee89779a6ff736229904aa7938
- v5_stop10_run1_fifo_pace3_summary.csv: 7d50f4e4f281d527597bda6537858c1a4982862c53c68e9c6ce9b30863bdaa25
