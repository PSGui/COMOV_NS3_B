# P3 — Auditoria dos oito pilotos e diagnóstico ARP do fading

**Data:** 26/11/2026. **Aim original:** *Find out whether storing data on the bus makes better use of Wi-Fi contact at a stop.*

Fonte primária: ficheiro enviado pelo grupo `p3_pilots_v15_stop0_run1_complete.zip`, contendo 81 entradas (80 ficheiros de ensaio e manifest SHA-256). A auditoria verificou **80/80 hashes**. Foram inspecionados os sumários dos oito casos, os eventos brutos de associação e as quatro capturas PCAP do cenário com fading. **Estes são pilotos run=1; não têm IC95%**.

## 1. Comparação dos oito pilotos (15 m/s, paragem de 0 s, run=1)

| Experiência | Política | Recebidas únicas até 60 s | Taxa de entrega / 12000 | UDP aceites mas não observados | Overflow | Expiradas antes de envio |
|---|---|---:|---:|---:|---:|---:|
| Referência P3 | Imediato | 1533 | 12,775% | 93 | 0 | 0 |
| Referência P3 | FIFO 4 MB / 2 ms | 5530 | 46,083% | 96 | 2374 | 4000 |
| A: Nakagami m=1 | Imediato | **0** | **0%** | 1829 | 0 | 0 |
| A: Nakagami m=1 | FIFO | **0** | **0%** | 5835 | 2165 | 4000 |
| B: STA concorrente 2 Mbit/s | Imediato | 1519 | 12,658% | 107 | 0 | 0 |
| B: STA concorrente 2 Mbit/s | FIFO | 4263 | 35,525% | 1363 | 2374 | 4000 |
| C: FIFO 3 ms, 4 MB | FIFO | 5109 | 42,575% | 311 | 2580 | 4000 |
| C: FIFO 2 ms, 2 MB | FIFO | 3530 | 29,417% | 96 | 6374 | 2000 |

O controlo P3 reproduz a P2 com 15 m/s e 0 s de paragem: 1533/5530 mensagens únicas recebidas, ambas as políticas com **16,2571 s de associação**. O código de base preservou a contabilidade original.

### Experiência B: concorrência

A estação concorrente enviou tráfego UDP para o mesmo AP, que recebeu **32499 pacotes** dessa origem. Distinguir *tráfego oferecido* de *tráfego efetivamente recebido*: a aplicação concorrente oferece 2 Mbit/s, não se presume que o canal forneça essa taxa líquida.

- Imediato: 1533→1519 mensagens recebidas (**−14**).
- FIFO: 5530→4263 (**−1267**).
- Vantagem FIFO no mesmo canal com concorrência: 4263−1519 = **+2744 mensagens**, contra +3997 sem concorrência.
- FIFO 4 MB mantém overflow 2374 e expirações 4000. O número de datagramas aceites pela socket mantém-se em 5626, mas **1363 desses não foram observados no AP** (contra 96 sem concorrência). A degradação principal é posterior à submissão UDP, e não overflow do buffer da aplicação.

**Conclusão piloto defensável:** a vantagem da FIFO persiste na presença de uma estação concorrente, mas o escoamento intensivo é mais vulnerável à capacidade partilhada do meio. Não atribuir os 1363 pacotes a um mecanismo MAC específico sem traces por pacote. Uma única run não demonstra estabilidade estatística.

### Experiência C: pacing/capacidade

- Aumentar pacing de 2 para 3 ms, mantendo 4 MB: receções 5530→5109 (**−421**), mais 206 mensagens expiradas ou descartadas pela aplicação conforme os contadores, e 311 datagramas aceites mas não observados (96 anteriormente). O ganho FIFO sobre imediato continua +3576.
- Reduzir FIFO de 4 para 2 MB, mantendo pacing 2 ms: receções 5530→3530 (**−2000**); overflow 2374→6374 (**+4000**); expirações 4000→2000 (−2000); ganho da FIFO vs imediato +1997.

**Conclusão piloto defensável:** o buffer só compensa plenamente quando a memória e o débito de descarga permitem preservar e escoar mensagens pré-associação. Ambos os limites degradam o resultado, mas a FIFO ainda supera o envio imediato nestas duas configurações.

## 2. Experiência A: zero receções não significa que fading invalida a FIFO

O cenário Nakagami m=1 produziu:
- Imediato: **1829** datagramas aceites por `SendTo`, **0** recebidos no AP.
- FIFO: **5835** aceites, **0** recebidos.
- Dois intervalos válidos de associação com duração total **18,28569 s**, e **3 callbacks DeAssoc adicionais** por execução, mesmo quando não havia associação aberta.
- O comportamento do radio nos PCAP não muda entre políticas antes da primeira transmissão IP bem-sucedida.

### Auditoria independente das quatro capturas Wi-Fi

As capturas são formato `DLT_IEEE802_11=105`. Os frames 802.11 foram classificados pelo Frame Control e, quando havia LLC/SNAP, por EtherType e opcode ARP:

| Política e rádio | Tramas capturadas | ARP Request | ARP Reply | Tramas IPv4 |
|---|---:|---:|---:|---:|
| Fading imediato — bus | 3811 | **28** | **0** | **0** |
| Fading imediato — AP | 2060 | **9** | **0** | **0** |
| Fading FIFO — bus | 3811 | **28** | **0** | **0** |
| Fading FIFO — AP | 2060 | **9** | **0** | **0** |

ARP requests contêm `10.8.0.2 → 10.8.0.1`, perguntando pelo MAC do AP, com retransmissões. **Não foi observada uma resposta ARP nem qualquer trama IPv4/UDP de payload B10**. Os 28/9 eventos nos PCAP do autocarro/AP são **eventos capturados nas respetivas interfaces**, não receções únicas de dados UDP nem estatísticas de erros PHY por si só.

A primeira associação ocorreu em t=60,8070 s e foi interrompida em 60,8224 s; depois houve nova associação em t=61,1806 s até t=79,4509 s. Os callbacks DeAssoc fora dos intervalos ocorreram em t=59,6981, 80,7255 e 81,9499 s. A origem desses callbacks adicionais deve ser interpretada com cuidado; o validador específico P3 regista-os sem falsificar a alternância entre estados.

**Diagnóstico localizado:** a resolução ARP não se completou; por isso **não existe evidência de UDP efetivamente colocado no ar** no ensaio com fading, embora a aplicação tenha aceitado envios UDP. Os PCAP não demonstram por que motivo o AP não gerou/forneceu resposta ARP (fading, estado de associação, retransmissões ou comportamento das camadas inferiores). A hipótese científica de fading prejudicar as entregas **não foi ainda testada de forma isolada**.

## 3. Controlo ARP opcional, sem modificar a referência

Para discriminar o efeito da resolução ARP do fading:

- O P3 mantém `staticArp=0` por defeito, **igual aos oito ensaios anteriores**.
- A opção `--staticArp=1` só é permitida com `scenario=fading`; utiliza `NeighborCacheHelper.PopulateNeighborCache()` depois de configurar as interfaces IPv4 (API de ns-3.48), antes de gerar tráfego UDP. A configuração coloca correspondências IP/MAC no cache sem trocas ARP dinâmicas. É **uma alteração experimental explícita**, não uma correção invisível dos resultados antigos.
- Executar **mais duas simulações** com a mesma velocidade, paragem, seed/run, canal e política, alterando só a disponibilidade inicial do ARP. Os resultados têm sufixo `_staticarp`, nunca substituem os originais.
- O novo script `scripts/run_p3_arp_diagnostic.py` valida as duas execuções, compara os sumários e conta ARP/IPv4 nos PCAP de cada rádio. Produz automaticamente **um único ZIP com resultados dinâmicos e estáticos**.

### Comando único de diagnóstico no WSL (após integrar o PR)

~~~bash
cd ~/COMOV/Project_B/COMOV_NS3_B
git pull
python3 scripts/test_p3_arp_diagnostic.py
python3 scripts/run_p3_arp_diagnostic.py ../../ns-3 --run 1 --skip-existing
~~~

Último comando produz `out/p3/p3_fading_arp_diagnostic_run1_complete.zip`. Enviar **só esse ZIP** para auditoria. Se o C++ não compilar, enviar o erro integral. **O controlo ARP ainda não foi executado no WSL** nesta revisão.

Se surgirem tramas IPv4/UDP e mensagens recebidas após pré-popular ARP, ficará demonstrado que a resolução ARP foi o bloqueio imediato na experiência anterior, mas isso não validará automaticamente a distribuição do canal Rayleigh nem permitirá concluir que o fenómeno ocorre numa estrada real.

Se as receções continuarem nulas, o diagnóstico deverá prosseguir ao nível de MAC/PHY, mesmo com ARP pré-resolvido.

## 4. Próxima decisão

As experiências **B e C** já dão evidência experimental preliminar de limites reais **do modelo simulado** à utilidade da FIFO: contenção do canal, pacing e capacidade de armazenamento.

A experiência **A permanece inconclusiva** até testar o controlo ARP e examinar as respetivas capturas. Não realizar 10 runs do fading defeituoso e calcular IC95% de zeros.

Os resultados são estritamente pilotos `run=1`, não inferência estatística. Depois de confirmar o funcionamento efetivo do fading, as três experiências poderão receber 10 runs emparelhadas de cada política, com análises de goodput por segundo associado, atraso e descartes.

