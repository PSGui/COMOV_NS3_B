# B10 / P3 — Fading m=3/5: auditoria e desenho das dez repetições emparelhadas

**Aim original:** *Find out whether storing data on the bus makes better use of Wi-Fi contact at a stop.*

**Origem dos números nesta secção:** ZIP entregue pelo grupo `p3_fading_severity_run1_complete.zip`, SHA-256 `32a9fd916959b23b62edad51c1fdd129e0da1b8b8b1724459149ee4fa71681d4`. São 97 ficheiros + manifesto, **97/97 hashes válidos**. Foram examinados os sumários, associações STA, receções UDP, logs MAC/IP da variante estática e capturas Wi-Fi AP/autocarro. São apenas pilotos run=1; não há IC95% ainda.

## 1. Resultado de fading m=3 e m=5

| Fading | ARP | Imediato UDP no prazo | FIFO UDP no prazo | Vantagem FIFO (mensagens) | Ganho FIFO (pp / 12000) |
|---|---|---:|---:|---:|---:|
| m=3 | dinâmico | **0** | **0** | não avaliável | não avaliável |
| m=3 | pré-configurado | 1555 | 5028 | +3473 | +28,942 |
| m=5 | dinâmico | **1666** | **5412** | **+3746** | **+31,217** |
| m=5 | pré-configurado | 1662 | 5436 | +3774 | +31,450 |

A 15 m/s, stop 0, referência P2 run=1 sem fading: immediate **1533** receções e FIFO **5530**, ganho +3997 mensagens. Com fading m=5 e ARP dinâmico o ganho cai para +3746, mas a FIFO continua a entregar mais informação no prazo. O cenário **m=5 com ARP dinâmico** é agora a variante de fading escolhida para a experiência A replicada; não foi calibrada a partir de medições rodoviárias.

**Não confundir taxa de entrega e bom uso do contacto:** o m=5 dinâmico, run=1, teve STA associada 17,398 s (immediate) e 17,604 s (FIFO), goodput no prazo 0,766/2,459 Mbit/s de payload por segundo associado. Os tempos de associação **não são idênticos entre políticas sob fading**; o contraste de políticas inclui interações entre a aplicação e dinâmica MAC. Goodput não equivale a ocupação PHY.

### Porque m=3 com ARP dinâmico não é 'FIFO sem vantagem'

No m=3 com ARP dinâmico, a STA reporta 19,678 s de associação em ambas as políticas, com **1968/5968 datagramas aceites pela socket, mas zero recebidos no AP**. Os PCAP do autocarro têm **23 ARP Requests**, os do AP têm **6 ARP Requests**, e ambos registam **zero ARP Replies e zero frames IPv4**. Sem resolução ARP, o sistema não completou a etapa necessária à transmissão IP. Esta run descreve **falha de estabelecimento de comunicação útil**, não uma comparação independente do buffer. Repetir zeros e calcular IC95% de entrega FIFO vs imediato aqui seria enganador.

Com ARP estático, m=3 passou a receber 1555/5028 datagramas no prazo, mas também alterou durações de associação (17,537/18,101 s) e tráfego no canal. Os traces do AP no ensaio estático confirmam entrega MAC/IPv4/UDP (1555/5028), com 123/205 `MacRxDrop`. ARP estático serve como **controlo de diagnóstico**, não como cenário de rede automaticamente mais realista.

Com m=5 **e ARP dinâmico**, os PCAP mostram pedidos e respostas ARP (2 pedidos e 7 respostas capturados no AP para cada política), além de frames IPv4 efetivos. As 1666/5412 receções UDP confirmam que há comunicação operacional.

## 2. Próxima etapa — os três testes com dez runs emparelhadas

Para evitar sobreinterpretar run=1, o script executa todos os oito casos seguintes para **cada run de 1 a 10**, sempre seed=1, velocidade 15 m/s, stop=0, 12000 mensagens geradas, 1000 B por mensagem, prazo de 60 s:

| Caso | Propagação / canal | Política | Pacing | Buffer |
|---|---|---|---:|---:|
| 1 | log-distance referência | imediato | 2 ms | 4 MB |
| 2 | log-distance referência | FIFO | 2 ms | 4 MB |
| 3 | log-distance + Nakagami m=5, **ARP dinâmico** | imediato | 2 ms | 4 MB |
| 4 | log-distance + Nakagami m=5, **ARP dinâmico** | FIFO | 2 ms | 4 MB |
| 5 | log-distance + segunda STA UDP 2 Mbit/s | imediato | 2 ms | 4 MB |
| 6 | log-distance + segunda STA UDP 2 Mbit/s | FIFO | 2 ms | 4 MB |
| 7 | log-distance referência | FIFO | 3 ms | 4 MB |
| 8 | log-distance referência | FIFO | 2 ms | 2 MB |

**Total:** 8×10 = 80 simulações. A primeira run de cada caso já existe, pelo que `--skip-existing` deverá reutilizar os oito resultados e calcular somente **72 execuções novas**. Nenhum CSV original P2 é sobrescrito. O controlo P3 é comparado **run a run** com os CSV originais P2: o script falha se contagens ou tempo associado forem diferentes.

## 3. Métricas e estatística

Para cada execução, o agregador produz: mensagens únicas recebidas dentro de 60 s, % / 12000 geradas, duração associada, **goodput útil no prazo por segundo associado**, atraso médio/P95 **só das mensagens recebidas**, contagens de enfileiradas/overflow/expiradas, aceitadas pela socket mas não observadas, receções da STA concorrente, eventos de associação e se houve **pelo menos uma receção UDP**.

Os comparadores estatísticos emparelham por número de run (não por instante de associação) e estimam médias e IC95% Student-t dos **ganhos em pontos percentuais**:

- referência FIFO vs imediato;
- fading m=5 dinâmico FIFO vs imediato;
- concorrência FIFO vs imediato;
- FIFO com pacing 3 ms vs imediato de referência;
- FIFO com buffer 2 MB vs imediato de referência.

Além disso, calculam a mudança do **ganho FIFO** face à referência para fading/concorrência (diferença de diferenças emparelhada) e a perda de entrega causada especificamente por pacing 3 ms ou capacidade 2 MB (comparação com FIFO 2 ms/4 MB de referência).

**Política de análise de falhas de ligação:** runs com zero UDP recebido **não são removidas** do cálculo de entrega. São assinaladas `contact_success=0` e contam como zero entrega do sistema completo. O goodput só é definido se existir tempo de associação maior que zero; não se inventa divisão por zero. O número de runs bem-sucedidas por política é reportado separadamente; se zero UDP ocorrer num lado, **não se deve automaticamente atribuir essa falha ao buffer**.

IC95% quantifica variabilidade induzida pelos seeds/algoritmos ns-3 escolhidos, **não generaliza a todo o tráfego e canal de uma via urbana**. Se os eventos de associação forem diferentes por política, a comparação mede o efeito total do sistema, não um ganho condicionado a um mesmo intervalo de cobertura.

## 4. Comandos exatos no WSL após integrar PR

```bash
cd ~/COMOV/Project_B/COMOV_NS3_B
git pull
python3 scripts/test_p3_repeated_tests.py
python3 scripts/run_p3_repeated_tests.py ../../ns-3 --start-run 1 --end-run 10 --skip-existing
python3 scripts/pack_p3_repeated_tests.py --start-run 1 --end-run 10
```

O programa é reiniciável: se for interrompido depois de várias runs válidas, repetir exatamente os mesmos comandos com `--skip-existing` evita duplicações. O empacotador produz um único ZIP: **`out/p3/p3_repeated_runs1-10_complete.zip`**.

Esse ZIP contém as 80 execuções P3 (CSVs e JSON individuais), 20 sumários P2 para controlo, três CSV de estatística, JSON de parâmetros e SHA-256. Inclui os PCAP do fading m=5 na run 1 e **dos eventuais casos m=5 com zero UDP** para diagnosticar perda de contacto. Não é necessário enviar outputs isolados.

**Estado:** scripts Python e CI verificados no GitHub; **as 72 novas simulações ainda precisam de ser corridas e validadas no WSL com ns-3.48**. Não antecipar conclusões estatísticas nem afirmar resultados reais.
