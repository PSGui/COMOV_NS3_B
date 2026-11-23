# P2 — Matriz completa dos 12 cenários (run=1)

**Data:** 23/11/2026. **Fonte:** output integral do comando `python3 scripts/run_p2_matrix.py ../../ns-3 --start-run 1 --end-run 1 --skip-existing` fornecido pelo grupo. **Estado:** 8 simulações novas e 4 reutilizadas; as 12 foram verificadas por `review_p2.py`, e os seis pares por `compare_p2.py`, todos com PASS. **Ainda não é uma análise estatística**: há somente uma run por condição.

## 1. Matriz consolidada

Cada execução gera 12 000 mensagens de 1000 bytes, à taxa de 100/s durante [10,130) s. A entrega conta somente a primeira receção única no AP dentro de 60 s da geração. Para ambos os modos, IEEE 802.11g / 2,412 GHz, ERP-OFDM 6 Mbit/s, log-distance n=3, Pt=20 dBm, AP fixo, 4 MB de FIFO quando ativa, pacing 2 ms, seed=1 e run=1.

| v (m/s) | Paragem (s) | Entregues imediato | Entregues FIFO | Taxa imediato | Taxa FIFO | Diferença (mensagens) | Diferença (pp) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 0 | 4620 | 8312 | 38,5000% | 69,2667% | +3692 | +30,7667 |
| 5 | 10 | 5620 | 9312 | 46,8333% | 77,6000% | +3692 | +30,7667 |
| 5 | 30 | 7620 | 11312 | 63,5000% | 94,2667% | +3692 | +30,7667 |
| 15 | 0 | 1533 | 5530 | 12,7750% | 46,0833% | +3997 | +33,3083 |
| 15 | 10 | 2533 | 6530 | 21,1083% | 54,4167% | +3997 | +33,3083 |
| 15 | 30 | 4533 | 8530 | 37,7750% | 71,0833% | +3997 | +33,3083 |

**Nota:** taxas calculadas como `100*N_received_on_time/12000`; as diferenças são diferenças emparelhadas de entrega, não PDR condicionado a mensagens enviadas. Não confundir chamadas à socket com entrega no AP. Todas as mensagens observadas neste conjunto foram recebidas antes dos respetivos prazos de 60 s.

## 2. Ocupação, overflow e expiração FIFO

| v (m/s) | Paragem (s) | Pico FIFO (MB decimais) | Overflow drop-newest | Expiradas antes de envio | Socket aceitou | Recebidas | Aceites mas não observadas |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 0 | 3,695 | 0 | 3589 | 8411 | 8312 | 99 |
| 5 | 10 | 3,695 | 0 | 2585 | 9415 | 9312 | 103 |
| 5 | 30 | 3,695 | 0 | 589 | 11411 | 11312 | 99 |
| 15 | 0 | 4,000 | 2374 | 4000 | 5626 | 5530 | 96 |
| 15 | 10 | 4,000 | 1371 | 4000 | 6629 | 6530 | 99 |
| 15 | 30 | 4,000 | 1239 | 2135 | 8626 | 8530 | 96 |

Conservação do caso extremo **v=15 m/s, paragem=0 s**: 12000 geradas = 9626 armazenadas + 2374 descartadas por overflow; 9626 armazenadas = 5626 aceites na socket + 4000 expiradas; 5626 aceites = 5530 recebidas + 96 não observadas.

Conservação com **v=15 m/s, paragem=30 s**: 12000 geradas = 10761 armazenadas + 1239 overflow; 10761 = 8626 socket aceitou + 2135 expiradas; 8626 = 8530 recebidas + 96 não observadas.

## 3. Efeito da paragem — observação sob esta configuração

Nas seis condições, aumentar a paragem de 0 a 10 s aumenta as receções em **1000 mensagens** e aumentar de 10 a 30 s aumenta em **2000 mensagens**, independentemente da política.

Isto corresponde à taxa de geração fixa de 100 mensagens/s, durante o tempo adicional de contacto Wi-Fi fornecido pela paragem. Não extrapolar que o efeito será linear em qualquer canal: o fenómeno é característico do cenário determinístico com capacidade MAC suficiente para acompanhar a geração neste intervalo.

O **ganho absoluto da FIFO não muda com a duração da paragem** dentro de cada velocidade: +3692 mensagens a 5 m/s e +3997 mensagens a 15 m/s. O backlog gerado antes da associação tem o mesmo volume para cada velocidade, porque a posição inicial, a velocidade de aproximação e o instante de paragem (t=70 s) são idênticos entre durações de paragem; este backlog é escoado mesmo com s=0. A duração da paragem acrescenta sobretudo mensagens geradas durante o contacto que ambas as políticas entregam.

### A associação e a velocidade

| v (m/s) | Paragem (s) | Duração associada reportada |
|---:|---:|---:|
| 5 | 0 | 47,1657 s |
| 5 | 10 | 57,2001 s |
| 5 | 30 | 77,1681 s |
| 15 | 0 | 16,2571 s |
| 15 | 10 | 26,2923 s |
| 15 | 30 | 46,2603 s |

A duração associada **não é sinónimo de capacidade útil de entrega**; os CSV identificam blocos de mensagens aceites mas não recebidas perto do fim da associação.

### Critério de capacidade do buffer

A 5 m/s, máximo 3695 mensagens = 3,695 MB, sem overflow em qualquer paragem.

A 15 m/s, o limite de 4 MB é atingido antes da primeira associação. A FIFO descarta por drop-newest pelo menos **1239** mensagens durante a aproximação, independentemente da paragem. Paragens mais curtas provocam overflow adicional depois da desassociação. Assim, aumentar o tempo parado reduz overflow e expirações posteriores, mas **não recupera mensagens já descartadas antes da associação**.

## 4. Implicações para o relatório

**Suportado pelos resultados do piloto:** FIFO aumenta a entrega até 60 s em todos os seis pares; o aumento depende da velocidade e do backlog pré-associação; a paragem aumenta entregas em ambas as políticas; 4 MB é insuficiente para evitar overflow a 15 m/s; há custo em atraso e mensagens que expiram sem segunda associação.

**Não suportado ainda:** efeito médio estatisticamente significativo, faixa de cobertura universal, perda PHY comprovada para IDs não recebidos, ótimo global de 4 MB ou 2 ms, realismo de uma estrada física. Existe apenas um cenário de canal determinístico de referência.

## 5. Próximos passos e avaliação de variabilidade

1. Registar a matriz piloto em `out/p2/paired_statistics.csv`, **sem IC95%**, pois n=1.
2. Executar **apenas run=2** para os seis pares, mantendo as mesmas configurações.
3. Comparar diferenças de run=1 vs run=2; se forem exatamente iguais, investigar a origem da variabilidade antes de investir em muitas repetições. A variação aleatória de backoffs MAC sob canal determinístico pode produzir intervalos minúsculos ou nulos, e isso não significa ausência de incerteza real.
4. Após essa avaliação, executar runs 3 a 10 e calcular diferenças emparelhadas com IC95% Student-t; o intervalo só caracteriza a variabilidade existente no modelo simulado.
5. Robustez opcional: deslocamento do AP e propagação alternativa com shadowing/fading documentado, em experimentos independentes.

Comandos depois de integrar a atualização no GitHub, executados na raiz de COMOV_NS3_B:

~~~bash
# A matriz run=1 já foi executada; não é necessário repeti-la
python3 scripts/paired_statistics_p2.py --output-dir out/p2 --start-run 1 --end-run 1

# Ensaio de variabilidade (nova segunda run emparelhada)
python3 scripts/run_p2_matrix.py ../../ns-3 --start-run 2 --end-run 2
python3 scripts/paired_statistics_p2.py --output-dir out/p2 --start-run 1 --end-run 2

# Só depois de inspecionar os dois primeiros pares de cada condição:
python3 scripts/run_p2_matrix.py ../../ns-3 --start-run 3 --end-run 10
python3 scripts/paired_statistics_p2.py --output-dir out/p2 --start-run 1 --end-run 10
~~~

## Proveniência

- Resultado fornecido pelo grupo numa captura de terminal com 416 linhas, contendo execuções, PASS do `review_p2.py` e resultados do `compare_p2.py` para os seis pares.
- Quantidades acima resultam das contagens da execução e das comparações reportadas. **Os CSV brutos dos oito novos cenários ainda não foram carregados para esta auditoria documental**; a concordância interna é indicada pelos validadores executados no WSL.
