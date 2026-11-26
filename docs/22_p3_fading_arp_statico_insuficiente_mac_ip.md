# B10 P3 — Porque o ARP estático não resolveu o fading (MAC/IP diagnóstico)

**Fonte primária:** ZIP fornecido pelo grupo em 26/11/2026, `p3_fading_arp_diagnostic_run1_complete.zip`. Foram conferidos os **45 hashes SHA-256** do manifesto e inspecionadas as quatro execuções e respetivas capturas PCAP (ARP dinâmico vs ARP pré-preenchido, imediato vs FIFO). Esta experiência é **diagnóstico de pilha de rede**, não estimativa de desempenho nem prova de equivalência de canais reais.

## 1. Resultado observado

| Fading, 15 m/s, stop 0, run 1 | UDP aceites (ARP dinâmico → estático) | UDP recebidos (dinâmico → estático) | Frames IPv4 capturados no AP (dinâmico → estático) |
|---|---:|---:|---:|
| Immediate | 1829 → 1814 | **0 → 0** | **0 → 2303** |
| FIFO | 5835 → 5891 | **0 → 0** | **0 → 5246** |

Com ARP estático, os PCAP dos dois equipamentos já não contêm mensagens ARP. Os frames IEEE 802.11 observados no AP transportam IPv4 do autocarro `10.8.0.2` para o AP `10.8.0.1`, protocolo UDP com destino **porta 9010** e endereço MAC do AP `00:00:00:00:00:01`. No PCAP do AP, os 2303 frames IPv4 do imediato correspondem a aproximadamente **1740 IDs de mensagem distintos**, com retransmissões a nível MAC; os 5246 frames IPv4 da FIFO correspondem a **4828 IDs distintos**. Isto NÃO é contagem de datagramas entregue à aplicação: a aplicação recebeu zero em ambos.

A configuração do ARP foi portanto uma **causa/condição de bloqueio a montante**, mas **não foi suficiente** para restaurar entregas. A afirmação anterior de que resolver ARP resolveria o problema era uma hipótese e foi refutada por este controlo. O fading continua cientificamente inconclusivo.

### Porque precisamos do próximo diagnóstico?

Um PCAP em modo monitor não estabelece, por si só, que os datagramas foram aceites pela camada MAC e encaminhados ao IP do AP. No ns-3.48, `WifiMac` disponibiliza traces `MacPromiscRx`, `MacRx` e `MacRxDrop`, e a pilha IPv4 disponibiliza o trace `Rx`. Podemos observar onde a contagem deixa de avançar **sem alterar as decisões de encaminhamento**. Há também uma distinção entre o `StaWifiMac::IsAssociated()` usado no P3 e o estado de associação mantido no AP. [Referência Wi-Fi ns-3.48](https://fossies.org/dox/ns-3.48/classns3_1_1WifiMac.html), [traces IPv4 ns-3.48](https://fossies.org/linux/privat/ns-3.48.tar.bz2/ns-3.48/src/internet/model/ipv4-l3-protocol.h).

## 2. Instrumentação não invasiva

O PR acrescenta opção `--macDiagnostics=1`, **desligada por defeito e permitida apenas em fading+staticArp**. O código original P2, as 120 simulações, os oito pilotos P3 e o controlo ARP prévio não são alterados. Os novos ficheiros têm sufixo `_staticarp_macdiag`.

O P3 regista a cada 0,25 s as duas visões de associação (STA e AP), assim como contagens acumuladas:

- `bus_mac_tx` — pacotes entregues pela pilha superior à MAC da STA;
- `ap_mac_promisc_rx` — frames encaminhados em modo promíscuo pela MAC do AP;
- `ap_mac_rx` — pacotes entregues pela MAC do AP à pilha superior;
- `ap_mac_rx_drop` — pacotes descartados pela MAC do AP;
- `ap_ipv4_rx` — pacotes que atingem a camada IPv4 do AP;
- `ap_udp_unique_received` — datagramas únicos efetivamente entregues à aplicação B10.

Os contadores e os estados vão para `*_mac_path.csv` (801 amostras) e `*_mac_path_summary.csv` (totais), além dos PCAP Wi-Fi e CSV regulares. Não se alteram protocolos, geração, tempo, meio de propagação, buffer, pacing, ARP nem seed.

### Critério de diagnóstico

- Se `ap_mac_rx=0` mas o PCAP AP mostrar tramas IPv4, investigar aceitação/filtragem pela MAC do AP e sincronização entre associação da STA e AP.
- Se `ap_mac_rx>0` e `ap_ipv4_rx=0`, procurar o bloqueio na entrega do NetDevice ao IPv4.
- Se `ap_ipv4_rx>0` e `ap_udp_unique_received=0`, investigar IP/UDP (endereços, validação, checksum, ligação da socket e eventos de descarte).
- Comparar, ao longo de t≈60–80 s, `sta_associated` com `ap_recognizes_bus`: são estados diferentes e não podem ser substituídos um pelo outro.

**Atenção:** os traces AP MAC/IP são contadores de fronteira, não causais por si só. O diagnóstico requer também inspeção das capturas e estado de associação. O código novo ainda não foi compilado no ns-3.48 do grupo; a CI valida apenas Python/Bash e existência de instrumentação.

## 3. Comando único no WSL depois de integrar o PR

```bash
cd ~/COMOV/Project_B/COMOV_NS3_B
git pull
python3 scripts/test_p3_mac_path_diagnostic.py
python3 scripts/run_p3_mac_path_diagnostic.py ../../ns-3 --run 1 --skip-existing
```

Enviar **apenas** `out/p3/p3_fading_mac_path_run1_complete.zip`. Inclui os dois novos diagnósticos (immediate/FIFO), os dois controlos anteriores com ARP pré-configurado, os CSV de estados e os PCAP, mais resumos e hashes.

Não voltar a executar a matriz P2, não calcular IC95% com os zeros e não considerar os quadros de B/C inválidos devido ao erro isolado de A.
