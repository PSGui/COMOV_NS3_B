# P1 — Auditoria independente dos cinco CSV: v=5 m/s, paragem=10 s

**Data de análise:** 23/11/2026. **Base:** ficheiros CSV reais enviados pelo grupo, resultantes de execução ns-3.48 com IEEE 802.11g, modo ERP-OFDM 6 Mbit/s, 20 dBm, log-distance n=3, sem FIFO. **A validação Python reportou PASS.**

## Proveniência dos CSV

Os CSV foram recebidos como anexos; não são incorporados neste repositório (diretoria out/ ignorada pelo Git). Hash SHA-256 de cada ficheiro original:

| Ficheiro | SHA-256 |
|---|---|
| v5_stop10_run1_summary.csv | `36a13f54b34d34bdc04c56214db2fa89f320069d4d0e5f15d17a493659aa0b94` |
| v5_stop10_run1_association.csv | `d658ce8cd3dd7d2ca9dd9833b20ec61108eed2348a12bb945fa307f11e50a988` |
| v5_stop10_run1_generated.csv | `9fd9994a36d43212ebcfaf748f1746a47b9e710ae9b8e392b1d14e3ea618acbd` |
| v5_stop10_run1_mobility.csv | `f954ae947f8e3bfa24cd46acf639b67b7de31c85a4600a56fdb96b2b88ff2d4c` |
| v5_stop10_run1_received.csv | `c394608e382895e8d088fa33bb52439ecf1896a9e7afab6b481d2fec3f73c800` |

## Contabilização e métricas

| Grandeza | Valor |
|---|---:|
| Geradas (10,00–129,99 s) | 12 000 mensagens |
| Descartadas na aplicação por ausência de associação | 6 280 |
| Aceites pela socket | 5 720 |
| Socket rejeitou | 0 |
| Receções únicas no AP | 5 620 |
| Receções ≤60 s após geração | 5 620 |
| Receções tardias / duplicadas / malformadas | 0 / 0 / 0 |
| Aceites na socket mas não observadas no AP até 200 s | 100 |
| Entrega no prazo / geradas | **46,8333%** |
| Receção observada / aceites na socket | **98,2517%** |
| Payload útil entregue | **5 620 000 bytes (5,62 MB decimais)** |
| Payload útil gerado | **12 000 000 bytes (12 MB decimais)** |

Não designar 6 280 mensagens sem associação como perda de transmissão. Foram descartadas **antes da chamada a SendTo**. Não designar as 100 aceites/não observadas como perda rádio já identificada.

## Cronologia obtida dos CSV

| Evento | Tempo (s) | x do autocarro (m) | Distância 3D ao AP (m) |
|---|---:|---:|---:|
| Associação real (StaWifiMac Assoc) | 46,940679 | −115,296606 | 115,306363 |
| Primeira geração aceite e recebida (ID 3695) | 46,950000 | −115,250000 | 115,259761 |
| Primeira receção (ID 3695) | 46,961758 | aproximadamente −115,191209 | aproximadamente 115,200975 |
| Início da paragem | 70,000000 | 0 | 1,5 |
| Fim da paragem | 80,000000 | 0 | 1,5 |
| Última geração entregue (ID 9314) | 103,140000 | 115,700000 | 115,709723 |
| Última receção (ID 9314) | 103,141478 | aproximadamente 115,707392 | aproximadamente 115,717114 |
| Primeira geração aceite sem entrega (ID 9315) | 103,150000 | 115,750000 | 115,759719 |
| Última geração aceite sem entrega (ID 9414) | 104,140000 | 120,700000 | 120,709320 |
| Desassociação real (StaWifiMac DeAssoc) | 104,140776 | 120,703882 | 120,713202 |

**Tempo de associação efetiva:** 57,200098 s (=104,140776−46,940679).

**Intervalo entre primeira e última receção UDP:** 56,179720 s (=103,141478−46,961758). Não confundir esta medida com duração contínua comprovada de capacidade útil; apenas delimita receções observadas.

### Estrutura exata dos IDs

- IDs aceites na socket: **3695–9414**, sem intervalos em falta (5720 mensagens).
- IDs recebidos: **3695–9314**, sem intervalos em falta (5620 mensagens).
- IDs aceites mas não observados: **9315–9414**, exatamente **100 mensagens consecutivas**, geradas em [103,15,104,14] s.
- Diferença entre última receção e DeAssoc: aproximadamente **0,999298 s**.
- Até ID 9314, todas as mensagens aceites foram recebidas; **não foram detetadas perdas dispersas** no intervalo de entregas.

### Atrasos das mensagens efetivamente recebidas

- Mediana: aproximadamente **1,478 ms**.
- Máximo: **11,758 ms** (primeira mensagem recebida).
- Não há mensagens observadas com atraso superior a 60 s.

As métricas de atraso caracterizam **apenas mensagens recebidas**. Não permitem atribuir atrasos às mensagens não recebidas.

## Modelo de potência junto aos eventos relevantes

Em ns-3.48, com Pt=20 dBm, f=2,412 GHz, d0=1 m, n=3, para d≥1 m:

`P_r(d)[dBm] = 20 − 40,0953 − 30 log10(d/1 m)`.

- Na associação (d≈115,306 m): **−81,951 dBm**.
- Na última receção (d≈115,717 m): **−81,997 dBm**.
- Na geração da primeira mensagem não observada (d≈115,760 m): **−82,002 dBm**.
- Na desassociação (d≈120,713 m): **−82,548 dBm**.

Esta sequência é consistente com **uma fronteira prática de receção perto de −82 dBm para este conjunto de definições**. É uma inferência ligada **à configuração específica**, não uma medição de sensibilidade nominal ou um limiar universal de Wi-Fi. Confirmar por trace PHY/MAC antes de sustentar uma causa exata.

## Interpretação científica

**Observações suportadas pelos CSV:** o AP recebeu 5620 mensagens, de forma consecutiva, sem duplicações; não recebeu os 100 últimos datagramas aceites pela socket, enquanto a STA ainda se encontrava associada. Após sair da região de receções observadas, o estado MAC só transitou para desassociado aproximadamente 1 s mais tarde.

**Hipóteses ainda não verificadas:** sinal insuficiente na extremidade da cobertura, retries que esgotam no MAC, descarte em fila MAC/PHY, mecanismo específico de deteção de beacons perdidos. A contagem de transmissões PHY, o número de tentativas, as falhas FCS e o estado das filas não constam destes CSV.

**Implicação para P2:** não usar apenas `IsAssociated()` como garantia de que a FIFO pode ser escoada com sucesso. Registar aceitação por socket, receção no AP e expiração de mensagens separadamente. Escolher pacing com cuidado e avaliar o atraso introduzido pelo próprio FIFO.

## Próxima experiência controlada

Depois de implementar FIFO, comparar em **mesma seed/run, trajetória, potência, frequência, geração e janela de observação** os dois comportamentos: descarte imediato sem associação e buffer FIFO de 4 MB com política drop-newest. O pacing proposto de **2 ms** equivale a carga de aplicação de **4 Mbit/s durante escoamento** (1000×8/0,002), abaixo de 6 Mbit/s PHY, mas **não prova capacidade MAC suficiente** por causa do overhead/ACK/contenção; validar antes de o fixar.

Repetir primeiro um par de pilotos (imediato/FIFO) para v=5 m/s e paragem de 10 s. Não iniciar as 12 configurações ×10 repetições antes de confirmar a semântica do buffer e a contabilidade dos logs.
