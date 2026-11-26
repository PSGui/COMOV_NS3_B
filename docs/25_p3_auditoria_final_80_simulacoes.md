# COMOV B10 — Auditoria final das 80 simulações P3

**Data de análise:** 26/11/2026. **Objetivo original:** *Find out whether storing data on the bus makes better use of Wi-Fi contact at a stop.*

**Evidência efetivamente recebida:** `p3_repeated_runs1-10_complete.zip`, SHA-256 do ZIP `3091c70854d42f0be9d0c6ab6e282633670c22216b0f1740bf27abb7207258f4`. Arquivo com 778 entradas: 776 ficheiros de origem incluídos no manifesto, `P3_REPEATED_README.txt` e manifesto. **776/776 hashes SHA-256 coincidentes; ZIP sem corrupção.** São 80 combinações (8 casos × runs 1..10); os dois controlos P2 de cada run também estão incluídos. Esta documentação baseia-se nos CSV individuais e PCAPs, não apenas no `paired.csv` agregado.

## 1. Validação independente

- Recontadas as 12 000 linhas de mensagens geradas por cada execução e as mensagens únicas recebidas dentro de 60 s em cada um dos 80 CSV individuais: **80/80 concordam com os `summary.csv` e `runs.csv`**.
- Para cada uma das 10 runs, os sumários dos controlos P3 `reference` (immediate/FIFO) reproduzem os sumários P2 correspondentes, inclusive os contadores de entrega e duração de associação (**20/20 pares P2/P3**). A P2 original não foi alterada.
- Recalculadas independentemente as diferenças de entrega por run e os IC95% com Student-t (9 graus de liberdade), comparados com `p3_repeated_runs1-10_paired.csv` e `p3_repeated_runs1-10_effects.csv`. Diferenças apenas de arredondamento na terceira casa decimal por t crítico pré-tabular do script.
- Todas as execuções registam 12000 mensagens geradas; todos os pares foram formados com run igual e condições de referência idênticas.
- Foram inspecionados os **32 PCAP** das variantes fading m=5 incluídas na evidência (run1 + todas as runs sem receção). A ausência de IPv4 nos casos de zero receções foi verificada por parsing 802.11/LLC/SNAP, EtherType e opcode ARP.

## 2. Comparação direta da política FIFO contra envio imediato

| Condição | Imediato: entrega (%) | FIFO: entrega (%) | Ganho médio FIFO (pp) | IC95% Student-t do ganho (pp) | Runs com UDP no AP |
|---|---:|---:|---:|---|---:|
| Referência log-distance | 12,804 | 46,129 | **+33,325** | [33,319; 33,331] | 10/10 em ambas |
| Fading Nakagami **m=5**, ARP dinâmico | 4,091 | 13,347 | **+9,256** | **[−1,409; 19,920]** | **3/10 em ambas** |
| Concorrência com uma STA UDP a 2 Mbit/s | 12,636 | 35,593 | **+22,957** | [22,627; 23,287] | 10/10 em ambas |
| FIFO com pacing 3 ms, log-distance | 12,804 | 42,678 | **+29,873** | [29,840; 29,907] | 10/10 em ambas |
| FIFO de 2 MB, pacing 2 ms, log-distance | 12,804 | 29,463 | **+16,658** | [16,652; 16,665] | 10/10 em ambas |

Percentagem em relação às 12000 mensagens geradas; não à quantidade aceite por `SendTo`. As duas últimas linhas reutilizam o mesmo imediato do controlo log-distance, pois pacing/capacidade só afetam FIFO. Um IC estreito não caracteriza incerteza de propagação em estradas reais nem demonstra validade universal.

### Mudança de benefício relativamente ao cenário de referência (diferenças emparelhadas de diferenças)

| Perturbação | Efeito médio na melhoria da FIFO (pp) | IC95% do efeito (pp) |
|---|---:|---|
| Fading m=5 dinâmico | **−24,069** | [−34,735; −13,403] |
| Segunda STA concorrente | **−10,368** | [−10,699; −10,038] |
| Pacing 2→3 ms (efeito na entrega da FIFO) | **−3,452** | [−3,482; −3,421] |
| Buffer 4→2 MB (efeito na entrega da FIFO) | **−16,667** | [−16,667; −16,667] |

Os dois últimos efeitos referem-se à entrega absoluta da FIFO, não à mesma definição de diferença-de-diferenças de duas políticas. A diferença exatamente constante de 2000 mensagens ao reduzir a capacidade de 4 MB para 2 MB é **estrutural nesta implementação e cenário**; o IC sem amplitude não representa certeza sobre outros percursos, prazos ou perfis de geração.

## 3. Experiência A — Fading: disponibilidade do contacto domina a média

Nas runs **1, 5 e 9** houve entrega UDP com as duas políticas; nas runs **2, 3, 4, 6, 7, 8 e 10** ambas entregaram **zero mensagens** apesar de a STA reportar cerca de 16–19 s de associação e de `SendTo` aceitar milhares de datagramas. A tabela abaixo usa números de mensagens únicas dentro do prazo:

| Run | Imediato | FIFO | FIFO−Imediato |
|---:|---:|---:|---:|
| 1 | 1666 | 5412 | +3746 |
| 2 | 0 | 0 | 0 |
| 3 | 0 | 0 | 0 |
| 4 | 0 | 0 | 0 |
| 5 | 1594 | 5177 | +3583 |
| 6 | 0 | 0 | 0 |
| 7 | 0 | 0 | 0 |
| 8 | 0 | 0 | 0 |
| 9 | 1649 | 5427 | +3778 |
| 10 | 0 | 0 | 0 |

Quando o contacto foi funcional (apenas runs 1/5/9), a vantagem média da FIFO foi **3702,33 mensagens**, equivalentes a **+30,853 pp** sobre 12000 geradas. **Esta é uma média condicionada a sucesso observado, não representa o desempenho esperado de uma passagem escolhida aleatoriamente.** A média de todas as dez runs é apenas +1110,7 mensagens / +9,256 pp.

**Diagnóstico dos PCAP dos sete casos falhados:** em ambos os modos, foram observadas ARP Requests no AP e na STA, mas **zero ARP Replies e zero tramas IPv4 nos dois PCAP**; por exemplo, na run2 o AP capturou 8/9 pedidos ARP (immediate/FIFO), sem respostas. O bloqueio imediato da transmissão IP está na resolução de endereços/ligação; a origem última pode envolver confirmação de associação MAC/ACK sob fading. **Não foi provado que todos os zeros têm exatamente a mesma causa interna**, porque estes ensaios dinâmicos não contêm os traces de estado MAC/IP do AP usados nos diagnósticos anteriores.

**Consequência estatística:** as diferenças de entrega no fading são 7 zeros e 3 valores positivos (~3600–3800). O IC Student-t [−1,409; 19,920] pp inclui zero, mas a distribuição é muito assimétrica e discretizada, violando a adequação habitual do IC t com n=10. **Não inferir que FIFO é equivalente ao imediato nem que traz benefício estatisticamente comprovado com 95% de confiança no cenário global.** Também não descartar os sete zeros para obter um IC artificialmente favorável. A conclusão correta é que a disponibilidade do contacto útil depende fortemente das realizações do modelo, limitando o benefício fim-a-fim do buffer. Foram 3/10 runs com UDP entregue, proporção empírica, **não uma taxa medida de falha de ligação em estrada real**.

### Questão física crucial

`StaWifiMac::IsAssociated()` e o tempo registado em associação não garantem que o AP esteja efetivamente a aceitar dados da STA. O resultado de zero UDP com ~18 s de associação e sem IPv4 reforça a distinção **associação reportada pela STA ≠ contacto Wi-Fi aproveitável para a aplicação**. Isto é especialmente importante para interpretar o goodput calculado por segundo de associação.

## 4. Experiência B — Concorrência MAC

Uma segunda estação associada ao mesmo AP envia tráfego UDP oferecido a 2 Mbit/s; o AP recebeu **32498–32499** datagramas concorrentes por run. Com dez runs:

- Imediato: 1536,5→**1516,3** mensagens recebidas (−20,2).
- FIFO: 5535,5→**4271,1** (−1264,4).
- Benefício adicional FIFO sob concorrência: **+2754,8 mensagens**, ou +22,957 pp, em todas as dez runs. CI95% [22,627; 23,287] pp.
- FIFO goodput útil por segundo associado: 2,712→**2,101 Mbit/s**; está disponível menos capacidade útil durante o contacto, embora o tempo associado permaneça praticamente igual.
- A FIFO apresenta ~**1356** datagramas aceites pela socket mas não observados no AP, contra ~98 na referência; overflow médio mantém-se próximo de 2373 mensagens. **Não atribuir os datagramas não recebidos exclusivamente a colisões** sem traces de perdas MAC/PHY por causa.

**Conclusão:** a vantagem da FIFO persiste sob uma estação concorrente no modelo simulado, mas é consideravelmente reduzida pela disputa do recurso rádio.

## 5. Experiência C — Limites de escoamento e memória

| Métrica (média nas 10 runs) | FIFO referência (2ms/4MB) | FIFO pacing 3ms/4MB | FIFO 2ms/2MB |
|---|---:|---:|---:|
| UDP no prazo | **5535,5** | **5121,3** | **3535,5** |
| Goodput por segundo associado | 2,712 Mbit/s | 2,509 Mbit/s | 1,732 Mbit/s |
| Overflow de buffer | 2366,6 | 2555,7 | **6366,6** |
| Expiradas antes do envio | 4000 | 4000 | 2000 |
| UDP aceites mas não observados | 97,9 | 323,0 | 97,9 |
| Atraso médio **entre mensagens recebidas** | 26,986 s | **31,725 s** | 25,362 s |
| Média dos P95 por run (recebidas) | 50,132 s | 50,559 s | 50,932 s |

- **Pacing 3 ms:** reduz entregas em média **414,2 mensagens** ou −3,452 pp, e aumenta atraso médio dos dados recebidos em +4,739 s. Aumenta também pacotes aceites pela socket mas não observados. O mecanismo de perda exato não pode ser inferido apenas do contador agregado.
- **Buffer 2 MB:** reduz entregas em **exatamente 2000 mensagens em cada run** e aumenta overflow em exatamente 4000 mensagens em cada run, segundo o padrão do modelo e FIFO drop-newest. Apesar disso, continua a entregar mais 1999 mensagens (média) do que a política imediata.
- Cuidado: a média de atraso da FIFO 2MB é ligeiramente menor que a de 4MB porque o conjunto de mensagens efetivamente recebido é diferente (viés de composição); **não concluir que diminuir buffer acelera a transmissão**.

## 6. Resposta final ao objetivo — com condições

**Resultado experimental demonstrado:** em todos os 10 pares sem fading e em todos os 10 pares com concorrência, o armazenamento FIFO entregou mais payload dentro de 60 segundos do que o imediato. A vantagem é maior quando existe backlog pré-associação que o sistema consegue conservar e escoar durante contacto utilizável. O ganho é reduzido ao partilhar o Wi-Fi, espaçar transmissões ou diminuir memória.

**Limite de aplicabilidade:** sob fading Nakagami m=5, com ARP dinâmico e os parâmetros fixos, a disponibilidade da ligação útil falhou em 7/10 runs para ambas as políticas; nelas o buffer não podia produzir entregas. Nas 3 runs em que houve UDP, a FIFO recuperou ~3702 mensagens adicionais em média; no conjunto de 10, o IC95% t da melhoria inclui zero e é inadequado como prova de ganho universal.

**Não demonstrado:** ocupação PHY verdadeira (airtime), comportamento de uma rede rodoviária real, qualidade de ligação com shadowing correlacionado, múltiplos autocarros, fairness, ou otimização ótima de tamanho/pacing. O goodput reportado é **payload da aplicação recebido no prazo por segundo de associação STA**, não taxa física nem eficiência espectral. A expiração aos 60s e descartar mensagens que excedem a fila são **políticas explícitas**, não propriedades universais do conceito de buffer.

### Enquadramento recomendado para apresentação/relatório

1. Baseline responde 'vale a pena guardar dados?' com **sim, neste modelo controlado** (FIFO +33,325 pp em v15/stop0).
2. A pergunta crítica é 'e se o contacto Wi-Fi não for confiável e houver restrições de capacidade?'.
3. O P3 mostra três limites: **conectividade/acesso MAC e ARP** (fading), **capacidade partilhada** (tráfego concorrente), **limitações locais de buffer e pacing**.
4. Conclusão: **o armazenamento melhora o aproveitamento do contacto quando há ligação útil e capacidade suficiente, mas não garante entrega quando o próprio acesso à rede falha e aumenta substancialmente os atrasos**.

## 7. Estado e próximos passos

**A matriz principal e as três experiências P3 estão concluídas para o desenho experimental especificado (v15 m/s, stop0 s, 10 runs).** Não repetir por rotina: avançar para redação, figuras comparativas e discussão dos mecanismos e limitações. Se forem necessárias inferências mais amplas sobre fading ou comportamento real, isso requer um estudo metodológico separado (mais runs, MAC/PHY traces de estado do AP, canal calibrado e comparação condicionada a contactos úteis).

Resultados consultáveis em `out/p3/p3_repeated_runs1-10_runs.csv`, `_paired.csv`, `_effects.csv`; mantidos no WSL original, não adicionados automaticamente ao GitHub. Este documento regista a auditoria efetuada a partir do ZIP entregue.
