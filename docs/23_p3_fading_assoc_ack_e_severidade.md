# B10 / P3 — Diagnóstico do mecanismo de associação e ensaio de fading menos severo

**Aim:** Find out whether storing data on the bus makes better use of Wi-Fi contact at a stop.

## 1. Dados confirmados do último diagnóstico (26/11/2026)

Origem: ZIP do grupo `p3_fading_mac_path_run1_complete.zip`, 33 ficheiros, **33/33 hashes SHA-256 válidos**. Ambos os casos são v=15 m/s, stop=0, run=1, Nakagami m=1, ARP pré-configurado, 12000 mensagens. As simulações com contadores adicionais reproduziram exatamente os resultados sem contadores.

| Métrica | Immediate | FIFO |
|---|---:|---:|
| Submissões MAC no autocarro | 1814 | 5891 |
| Descarta na MAC do AP | 1740 | 4829 |
| Entregues pela MAC do AP | **0** | **0** |
| Entregues ao IPv4 do AP | **0** | **0** |
| Recebidas na aplicação do AP | **0** | **0** |
| Amostras do autocarro com estado associado (250 ms) | 72/801 | 75/801 |
| Amostras do AP que reconhece o MAC do autocarro | **0/801** | **0/801** |

Os descartes MAC do AP crescem continuamente entre aproximadamente t=61 e t=80 s, durante o período em que a STA acredita estar associada. Isto localiza a falta de entrega antes da camada IPv4 e evidencia divergência entre os estados de associação da STA e AP. A amostragem de 250 ms **não exclui transições muito curtas do AP**; os descartes ao longo de toda a janela são a evidência complementar.

### Inspeção independente dos frames de associação

Foram descodificados os PCAP IEEE 802.11: o AP recebe Association Requests e envia Association Responses com código de estado 0 (sucesso), mas retransmite as respostas repetidamente. No intervalo t=60 a 62 s, em cada política, o PCAP AP contém **14 transmissões de Association Response, das quais 12 têm o bit Retry ativo**. O PCAP STA observa algumas respostas e contém ACKs endereçados ao AP. O PCAP do AP **não regista ACKs endereçados ao próprio AP** nesse intervalo (apesar de conter ACKs destinados à STA).

Este padrão é consistente com a resposta de associação ter sido recebida pela STA mas **não confirmada por ACK no AP**. No ns-3.48, `ApWifiMac::TxOk()` marca a STA como associada quando a Association Response é confirmada por ACK; `TxFailed()` considera a STA ainda não associada quando esse envio falha. Isto sustenta a hipótese de dessicronização de estados por falhas de ACK das respostas de associação **sob fading m=1**. Não interpretamos zero UDP como uma medição isolada da capacidade da FIFO.

Referência da API `ApWifiMac`, métodos `TxOk` e `TxFailed`: https://www.qkdnetsim.info/html/db/d72/classns3_1_1_ap_wifi_mac.html . Implementação e estado `GOT_ASSOC_TX_OK` do gestor de estações: https://fossies.org/linux/privat/ns-3.48.tar.bz2/ns-3.48/src/wifi/model/wifi-remote-station-manager.cc .

## 2. Próxima experiência — gravidade controlada do fading

Não corrigir artificialmente a associação nem eliminar o resultado severo de m=1: esse resultado mostra um possível limite da própria **conectividade** neste modelo ns-3. Em vez disso, testar duas intensidades predefinidas de Nakagami com m0=m1=m2: **m=3 e m=5**, mantendo trajetória, seed/run, geração, PHY 802.11g a 6 Mbit/s, potência, buffer e pacing.

Cada valor m é testado com **immediate e FIFO**, primeiro com ARP dinâmico (representativo do funcionamento normal) e em seguida com ARP pré-configurado (controlo de resolução de endereços, não cenário real). Total **8 novas simulações** com run=1. Nas variantes com ARP pré-configurado ativam-se apenas os traces passivos MAC/IP. A baseline P2 e os oito pilotos P3 permanecem inalterados. Todos os resultados novos têm sufixo `_m3` ou `_m5`.

| Nº | Nakagami m | ARP | Política | Objetivo |
|---:|---:|---|---|---|
| 1 | 3 | Dinâmico | Imediato | Contacto e entrega com fading moderado |
| 2 | 3 | Dinâmico | FIFO | Ganho FIFO vs imediato com m=3 |
| 3 | 3 | Pré-configurado | Imediato | Isolar dependência de ARP no m=3 |
| 4 | 3 | Pré-configurado | FIFO | Isolar dependência de ARP no m=3 |
| 5 | 5 | Dinâmico | Imediato | Contacto e entrega com fading menos severo |
| 6 | 5 | Dinâmico | FIFO | Ganho FIFO vs imediato com m=5 |
| 7 | 5 | Pré-configurado | Imediato | Isolar dependência de ARP no m=5 |
| 8 | 5 | Pré-configurado | FIFO | Isolar dependência de ARP no m=5 |

## 3. Comandos únicos no WSL (após integrar PR)

```bash
cd ~/COMOV/Project_B/COMOV_NS3_B
git pull
python3 scripts/test_p3_fading_severity.py
python3 scripts/run_p3_fading_severity.py ../../ns-3 --run 1 --skip-existing
```

O executor produz `out/p3/p3_fading_severity_run1_complete.zip`: oito resumos/traces/PCAP, os contadores MAC/IP dos quatro controlos com ARP estático, um CSV comparativo e manifesto SHA-256. **Enviar apenas esse ZIP**. Se a compilação C++ falhar, enviar o erro integral: GitHub CI não compila ns-3.48.

## 4. Critérios de interpretação

- Uma ligação só é aproveitável se o AP confirmar associação e entregar datagramas. Um estado associado apenas na STA **não garante** oportunidade de transmissão útil.
- Para os testes com ARP **dinâmico**, comparar immediate/FIFO dentro do mesmo m, observando receções únicas no prazo, tempos de associação e goodput por segundo associado. Se zero UDP persistir, reportar explicitamente que **não houve contacto utilizável** no piloto; não confundir com desempenho de buffer.
- Os testes ARP pré-configurado verificam se a resolução de endereços ainda é bloqueio independente da associação. As variantes com e sem ARP estático **não são uma comparação de políticas de armazenamento**.
- Reportar m=1 mesmo se m=3/m=5 resultarem melhor. Não escolher o cenário mais favorável e ocultar o severo.
- Não calcular IC95% com uma run; depois do diagnóstico decidir quais das variantes justificam runs 2–10. Não assumir que Nakagami m=3 ou m=5 representa condições reais sem calibração.

**Conclusão até agora:** sob fading m=1, o P3 produziu falta de estabelecimento consistente da associação do ponto de vista do AP, com descartes MAC de todos os dados. Isto aponta um limite de acesso ao meio separado do tamanho/capacidade da FIFO. O novo sweep investiga quando existe contacto útil suficiente para comparar novamente armazenamento e envio imediato.
