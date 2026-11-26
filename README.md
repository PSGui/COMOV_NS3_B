# COMOV_NS3_B — Projeto B10

**COMOV 2026/27: Bus Data Transfer at a Stop**

Estudo no ns-3 de transferência UDP entre um autocarro móvel e um AP Wi-Fi durante uma paragem, comparando **envio imediato** com **armazenamento FIFO de aplicação**.

> **Estado atual:** P0 e P1 validados no ns-3.48; **P2 concluiu as 120 simulações da matriz** (6 combinações velocidade/paragem ×2 políticas ×10 runs). As diferenças FIFO − imediato foram calculadas de forma emparelhada, com IC95%: **+30,774 pp a 5 m/s** e **+33,325 pp a 15 m/s** em qualquer duração de paragem, dentro do modelo. Faltam figuras finais, análise agregada do atraso e robustez da propagação; os IC95% não representam variabilidade de campo.

## Navegação

- [Objetivo, hipóteses e decisões](docs/01_escopo_e_decisoes.md)
- [Tabela rastreável de parâmetros](docs/02_parametros.md)
- [Modelo teórico e todas as contas principais](docs/03_modelo_teorico.md)
- [12 simulações obrigatórias, pilotos e robustez](docs/04_matriz_simulacoes.md)
- [Validação independente dos CSV do preflight](docs/05_validacao_preflight.md)
- [P0 — propagação no ns-3.48 e execução no WSL](docs/07_p0_ns3_48.md)
- [P0 — resultados observados, limites e correção de CSV](docs/08_resultados_p0_11g.md)
- [P1 — mobilidade contínua, associação e UDP](docs/09_p1_mobility_udp.md)
- [P1 — primeiros resultados do caso 5 m/s e paragem 10 s](docs/10_resultados_p1_piloto_v5_stop10.md)
- [P2 — implementação e validação proposta do buffer FIFO](docs/12_p2_fifo_comparacao.md)
- [P2 — resultados verificados e auditoria do primeiro par](docs/13_auditoria_p2_par_v5_stop10.md)
- [P2 — sensibilidade a pacing e velocidade: 21 CSV auditados](docs/14_sensibilidade_pacing_velocidade.md)
- [P2 — matriz completa de 12 simulações, run=1](docs/15_resultados_matriz_12_cenarios_run1.md)
- [P2 — resultados estatísticos das 10 runs e IC95%](docs/16_resultados_estatisticos_10_runs.md)
- [B10 — aproveitamento do contacto Wi-Fi e robustez ao deslocar AP](docs/17_contact_utilisation_and_ap_robustness.md)
- [B10 — auditoria dos 120 contactos e piloto AP ±30 m](docs/18_auditoria_contacto_wifi_e_robustez_piloto.md)
- [P3 — três testes críticos: fading, tráfego concorrente, buffer/pacing](docs/19_p3_tres_testes_criticos.md)
- [P3 — auditoria dos oito pilotos e diagnóstico ARP de fading](docs/21_p3_oito_pilotos_auditoria_arp.md)
- [P3 — ARP estático não resolveu o fading: diagnóstico AP MAC/IP](docs/22_p3_fading_arp_statico_insuficiente_mac_ip.md)
- [P3 — diagnóstico ACK de associação e variação Nakagami m=3/5](docs/23_p3_fading_assoc_ack_e_severidade.md)
- [P3 — auditoria m=3/5 e dez repetições emparelhadas dos três testes](docs/24_p3_fading_m5_e_dez_runs_paired.md)
- [P1 — auditoria independente dos cinco CSV e análise da fronteira −82 dBm](docs/11_auditoria_p1_csv_v5_stop10.md)
- [Referências e documentação ns-3](docs/06_referencias.md)
- [Configuração legível por máquina](params/reference.json)
- [Calculadora independente e geração de matriz CSV](scripts/preflight.py)

## Primeiros comandos (WSL)

```bash
git clone https://github.com/PSGui/COMOV_NS3_B.git
cd COMOV_NS3_B
python3 scripts/preflight.py
```

A calculadora usa apenas a biblioteca padrão Python. Produz `out/preflight/matrix.csv` (12 linhas) e `out/preflight/theory.csv`; **são resultados analíticos, não simulações**. Os ficheiros `out/` são descartáveis e não se devem confundir com os dados brutos das simulações.

## Regras de qualidade

1. Parametrizar tudo, nunca alterar manualmente os resultados em relatórios.
2. Justificar escolhas e guardar versão exata de ns-3, seed/run/streams.
3. Dar ID a todas as mensagens **na geração** e distinguir receção no prazo, tardia, drop e pendente.
4. Calcular a teoria **antes** de ver os resultados e guardar diferenças.
5. Uma execução = uma observação; diferenças emparelhadas e IC95%.
6. Nunca declarar validada uma simulação sem os logs e teste de reprodução.

## Fluxo Git

Criar branch por mudança, descrever pressupostos e validar alterações antes de integrar em `main`. No WSL usar `git pull` depois de integrar o pull request.

## Próximo desenvolvimento

Executar o código de P0 em `src/b10-p0-propagation.cc` com `bash scripts/run_p0.sh /caminho/para/ns-3.48` (ver guia P0). Após validação: implementar `src/b10-bus-stop.cc`, instrumentar UDP, mobilidade, associação e só depois FIFO.

## Enunciado

A ficha B10 exige as 12 combinações de velocidade, paragem e política, comparação do volume entregue e da entrega em 60 s, IC95%, acompanhamento do buffer e da associação, contabilidade e robustez deslocando AP. Relatório até 10 páginas (+ referências) e pacote reproduzível.

## Piloto P0 com ns-3.48

```bash
# No diretório COMOV_NS3_B, depois do merge da branch:
git pull
bash scripts/run_p0.sh /caminho/para/ns-3.48
```

O caminho tem de apontar para a instalação real do simulador. O script cria `out/p0/p0_11g.csv` e valida os resultados. P0 já compilou no WSL; a correção posterior do formato CSV exige nova execução. Para criar gráficos opcionais (requer `matplotlib`): `python3 scripts/plot_p0.py --input out/p0/p0_11g.csv --output-dir out/p0`.

## P1 — próximo piloto (sem buffer)

Depois de integrar o PR de P1:

~~~bash
cd ~/COMOV/Project_B/COMOV_NS3_B
git pull
bash scripts/run_p1.sh ../../ns-3 5 10
python3 scripts/plot_p1.py --prefix out/p1/v5_stop10_run1
~~~

O comando gera 12 000 mensagens de 1000 bytes entre 10 e 130 s, sem armazenamento na aplicação; regista associação, mobilidade e receção UDP até t=200 s. Verifica os CSV e cria três figuras separadas. O piloto P1 **não tem resultados confirmados** antes da execução no WSL. Para testar só a validação dos dados com casos sintéticos (sem ns-3):

~~~bash
python3 scripts/test_p1_validation.py
~~~

## Correção do modo PHY após falha na primeira execução P1

Para IEEE 802.11g (2,4 GHz), usar `ErpOfdmRate6Mbps`; para IEEE 802.11a (5 GHz), `OfdmRate6Mbps`. O P0 inicial não enviou datagramas UDP, pelo que a incompatibilidade só se manifestou no P1 (t=46,959028 s). Depois de integrar a correção, correr novamente:

~~~bash
git pull
bash scripts/run_p1.sh ../../ns-3 5 10
~~~

O `run_p1.sh` copia sempre a versão atualizada do programa para o `scratch/` do ns-3 antes de o executar.

## Validar o P1 já executado (sem repetir a simulação)

Após merge da correção do validador:

~~~bash
git pull
python3 scripts/test_p1_validation.py
python3 scripts/review_p1.py --prefix out/p1/v5_stop10_run1 --require-contact
python3 scripts/plot_p1.py --prefix out/p1/v5_stop10_run1
~~~

Foi corrigido o nome `received_unique` da coluna no CSV de resumo. A execução e os CSV de P1 foram posteriormente auditados (ver [auditoria P1](docs/11_auditoria_p1_csv_v5_stop10.md)). Ver [resultados provisórios](docs/10_resultados_p1_piloto_v5_stop10.md).

## P2 — primeiro par executado e auditado

Os seguintes comandos reproduzem o primeiro par; **não é necessário repetir as simulações para analisar os CSV já gerados**:

~~~bash
cd ~/COMOV/Project_B/COMOV_NS3_B
git pull
python3 scripts/test_p2_validation.py
bash scripts/run_p2.sh ../../ns-3 immediate 5 10
bash scripts/run_p2.sh ../../ns-3 fifo 5 10
python3 scripts/compare_p2.py --immediate-prefix out/p2/v5_stop10_run1_immediate --fifo-prefix out/p2/v5_stop10_run1_fifo
python3 scripts/plot_p2.py --immediate-prefix out/p2/v5_stop10_run1_immediate --fifo-prefix out/p2/v5_stop10_run1_fifo --output-dir out/p2
~~~

O mesmo simulador P2 executa as duas políticas, com o mesmo seed/run. O validador reconstrói as operações de FIFO e distingue geração, submissão UDP e chegada ao AP. A compilação e os CSV deste par já foram analisados: 12 000 geradas por política, 5 620 receções imediatas e 9 312 com FIFO; o par adicional de 15 m/s e o controlo de pacing de 3 ms também foram executados; faltam paragens de 0 e 30 s e as repetições. Mais detalhes em [docs/12_p2_fifo_comparacao.md](docs/12_p2_fifo_comparacao.md).

### Diagnóstico aprofundado do P2

~~~bash
python3 scripts/compare_p2.py --immediate-prefix out/p2/v5_stop10_run1_immediate --fifo-prefix out/p2/v5_stop10_run1_fifo --output-json out/p2/v5_stop10_run1_pair_analysis.json
~~~

O comparador confirma paridade das trajetórias e eventos de associação com tolerância para diferenças de arredondamento da ordem de 1e-9, lista as sequências de IDs aceites mas não observados, quantifica mensagens recuperadas pré-associação, atraso de cauda e instante de esvaziamento do FIFO. A auditoria completa está em [docs/13_auditoria_p2_par_v5_stop10.md](docs/13_auditoria_p2_par_v5_stop10.md). Os controlos de pacing de 3 ms e velocidade de 15 m/s foram concluídos; falta comparar paragens 0 e 30 s e depois realizar ≥10 runs emparelhadas por cenário.

## P2 — 120 simulações e intervalos de confiança (concluído)

As 10 runs de cada cenário foram executadas no WSL. A análise estatística emparelhada está disponível em `out/p2/paired_statistics.csv`. As médias de melhoria em entrega no prazo são +30,774 pp para 5 m/s (IC95% [30,761;30,787]) e +33,325 pp para 15 m/s (IC95% [33,319;33,331]). Ver [resultados de 10 runs](docs/16_resultados_estatisticos_10_runs.md).

**Não executar novamente a matriz sem necessidade.** Para rever a tabela já calculada:

~~~bash
python3 - <<'PY'
import csv
with open("out/p2/paired_statistics.csv", newline="") as file:
    for row in csv.DictReader(file):
        print(row)
PY
~~~

Faltam apresentação gráfica, estatísticas de atraso por cenário agregadas sobre 10 runs e análise de robustez. Os IC95% são condicionados ao modelo ns-3 usado (canal sem fading/shadowing), não à incerteza de uma estrada real.

## Figuras finais a partir das 10 runs

Após integrar o PR, basta executar o gerador sobre o ficheiro `paired_statistics.csv` já criado. **Não repetir as 120 simulações.**

~~~bash
python3 scripts/plot_paired_statistics.py --input out/p2/paired_statistics.csv --output-dir out/p2
~~~

Produz `comov_entrega_media_politicas.png`, `comov_ganho_fifo_ic95.png` e `comov_fifo_overflow_expiracao.png`. O IC95% do segundo gráfico refere-se à **diferença FIFO−imediato**, não às taxas médias individuais. Para média e P95 de atrasos nas 10 runs serão necessários os CSV `*_received.csv`, não incluídos no ficheiro estatístico agregado.

## Conclusão da análise de contacto — resultados verificados

Foram recebidos e auditados os três CSV de contacto relativos às **120 execuções** e o resumo do piloto AP deslocado (8 novas simulações, run=1). Resultado do objetivo principal: **a FIFO entrega mais payload útil por segundo de associação em todos os seis cenários**.

- A 5 m/s, goodput útil no prazo de 1,410/1,302/1,173 Mbit/s na FIFO, contra 0,784/0,786/0,790 com envio imediato, para paragens 0/10/30 s;
- A 15 m/s, 2,712/1,985/1,474 Mbit/s na FIFO, contra 0,753/0,771/0,783 com envio imediato;
- Atraso médio FIFO de 7,53 a 26,99 s consoante velocidade e paragem, face a aproximadamente 1,5 ms de imediato;
- Piloto AP ±30 m e v=15 m/s, s=0/30 s: ganho de +3997 mensagens em cada par deslocado (run=1), mas diferenças de até 401 descartes por overflow entre −30 e +30 m na paragem de 30 s.

**Goodput por segundo associado não mede ocupação do canal PHY.** Os IC95% estatísticos aplicam-se à matriz AP central, com 10 runs. O teste de deslocação do AP ainda tem apenas uma run e não permite generalização a canais urbanos.

Ver [auditoria dos resultados](docs/18_auditoria_contacto_wifi_e_robustez_piloto.md) para tabelas, IC95%, tempos e proveniência.

## Próxima fase: objetivo central — usar melhor o contacto Wi-Fi

**Aim:** *Find out whether storing data on the bus makes better use of Wi-Fi contact at a stop.*

As 120 simulações com AP em x=0 estão concluídas e o **contacto útil já foi calculado e auditado**. Os comandos seguintes apenas permitem reproduzir a análise com os CSV existentes:

~~~bash
python3 scripts/test_p2_contact.py
python3 scripts/analyze_p2_contact.py --input-dir out/p2 --output-dir out/p2 --start-run 1 --end-run 10
python3 scripts/plot_p2_contact.py --input out/p2/contact_metrics_summary.csv --output-dir out/p2
~~~

Isto produz `contact_metrics_runs.csv` (120 execuções), `contact_metrics_summary.csv` (12 grupos), `contact_metrics_pairs.csv` (6 diferenças emparelhadas e IC95%) e duas figuras. **Goodput útil por segundo de associação não representa ocupação PHY do canal.**

O piloto AP ±30 m para v=15 m/s e paragens 0/30 s **já foi executado** com run=1. O comando seguinte reproduz esses ensaios ou revalida as oito execuções existentes, com prefixos independentes:

~~~bash
python3 scripts/run_p2_ap_robustness.py ../../ns-3 --start-run 1 --end-run 1 --skip-existing
~~~

O protocolo e as ressalvas estão em [docs/17_contact_utilisation_and_ap_robustness.md](docs/17_contact_utilisation_and_ap_robustness.md). A política FIFO simulada **expira mensagens na fila aos 60 s**: não confundir com uma política que transmita mensagens já fora do prazo.

## P3 — Três cenários para testar os limites da vantagem FIFO

**Pergunta do enunciado:** *Find out whether storing data on the bus makes better use of Wi-Fi contact at a stop.* P2 já demonstrou ganho numa baseline sem fading nem tráfego concorrente; P3 investiga **quando essa vantagem diminui ou falha**. Não alterar nem repetir a baseline de 120 runs.

O P3 está isolado no código `src/b10-p3-stress.cc` e nos CSV da pasta `out/p3/`. Cada piloto usa **15 m/s, paragem 0 s, run=1**. O executador corre **8 simulações**: duas de controlo (para confirmar reprodução exata da P2); duas com Nakagami m=1; duas com outra STA a oferecer UDP 2 Mbit/s; e duas variantes FIFO separadas (pacing 3 ms/4 MB ou pacing 2 ms/2 MB). O P3 é código novo e precisa de validação C++ no ns-3.48 do grupo; GitHub Actions não compila ns-3.

Depois de integrar o PR:

~~~bash
cd ~/COMOV/Project_B/COMOV_NS3_B
git pull
python3 scripts/test_p3_pilots.py
python3 scripts/run_p3_pilots.py ../../ns-3 --speed 15 --stop 0 --run 1 --skip-existing
python3 scripts/pack_p3_results.py --speed 15 --stop 0 --run 1
~~~

**Único ficheiro a enviar:** `out/p3/p3_pilots_v15_stop0_run1_complete.zip`, que contém os CSV, os resumos e o manifesto SHA-256. Se o C++ não compilar, enviar o **erro completo do compilador**. O executor interrompe-se caso o controlo P3 não reproduza a P2 ou o AP não receba tráfego concorrente. O relatório de objetivos, hipóteses, parâmetros e resultados esperados está em [docs/19_p3_tres_testes_criticos.md](docs/19_p3_tres_testes_criticos.md).

## P3 — Pilotos executados e diagnóstico do fading (26/11/2026)

O ZIP real `p3_pilots_v15_stop0_run1_complete.zip` foi auditado (80/80 hashes de ficheiros válidos). A referência P3 reproduziu P2 exatamente, 1533 mensagens imediatas e 5530 FIFO entregues. Na concorrência (STA extra a oferecer 2 Mbit/s), a FIFO recebeu 4263 mensagens e o imediato 1519; o AP recebeu 32499 datagramas da STA concorrente. Reduzir FIFO a 2 MB entregou 3530; aumentar pacing para 3 ms, com 4 MB, entregou 5109. Ver [relatório P3](docs/21_p3_oito_pilotos_auditoria_arp.md).

**Atenção à Experiência A:** com Nakagami m=1, ambos os modos apresentaram 0 receções UDP apesar de 1829/5835 `SendTo` aceites. A análise dos PCAP mostrou **28 ARP Request capturadas no autocarro e 9 no AP, nenhuma ARP Reply e nenhuma trama IPv4**. O problema imediato é a resolução ARP incompleta; não reportar estes zeros como perda por fading. Introduziu-se um controlo *exclusivamente de diagnóstico*: `--staticArp=1` apenas no cenário fading, mantendo o parâmetro omisso/falso no P3 e em toda a P2.

~~~bash
cd ~/COMOV/Project_B/COMOV_NS3_B
git pull
python3 scripts/test_p3_arp_diagnostic.py
python3 scripts/run_p3_arp_diagnostic.py ../../ns-3 --run 1 --skip-existing
~~~

Enviar apenas `out/p3/p3_fading_arp_diagnostic_run1_complete.zip`, que contém os CSV, os PCAP e o manifesto SHA-256 do controlo ARP dinâmico vs estático. O controlo precisa ainda de compilação C++ e execução no WSL; a CI só verifica a parte Python e sintaxe Bash.

## P3 — Diagnóstico ARP estático: zero UDP apesar de tráfego 802.11 IPv4

Os resultados reais de `p3_fading_arp_diagnostic_run1_complete.zip` foram verificados (45/45 hashes): com ARP pré-configurado, **immediate 1814 aceites e 0 recebidos, FIFO 5891 aceites e 0 recebidos**. Os PCAP no AP já registam **2303 / 5246 frames Wi-Fi IPv4/UDP**, respetivamente, dirigidos a 10.8.0.1:9010. A resolução ARP já não é a explicação suficiente para as zero receções. As experiências B/C continuam válidas como pilotos; A permanece bloqueada e não pode gerar IC95% científicos.

O próximo controlo só acrescenta contadores e amostragem **passiva** dos traces AP MAC/IP e estado de associação do AP; executa duas novas runs com sufixos independentes `_staticarp_macdiag`:

~~~bash
cd ~/COMOV/Project_B/COMOV_NS3_B
git pull
python3 scripts/test_p3_mac_path_diagnostic.py
python3 scripts/run_p3_mac_path_diagnostic.py ../../ns-3 --run 1 --skip-existing
~~~

Enviar só `out/p3/p3_fading_mac_path_run1_complete.zip`. Ver [protocolo MAC/IP](docs/22_p3_fading_arp_statico_insuficiente_mac_ip.md). O novo C++ precisa ainda de compilar no WSL; GitHub Actions não executa ns-3.

## P3 — AP não confirma associação sob Nakagami m=1

O último ZIP `p3_fading_mac_path_run1_complete.zip` passou nos 33/33 hashes. Com fading Nakagami m=1 e ARP pré-configurado, o autocarro submeteu 1814 (immediate) ou 5891 (FIFO) pacotes à MAC, mas o AP registou **1740/4829 MacRxDrop**, **zero MacRx/IPv4/UDP** e **zero amostras de AP a reconhecer a STA como associada** (apesar de esta se considerar associada durante ~18 s). O PCAP do AP mostra retransmissões de Association Responses sem ACK observado no AP. Isto é consistente com o mecanismo ns-3.48 que só confirma associação no AP quando recebe ACK da Association Response. Ainda não é uma comparação válida de desempenho da FIFO.

Para identificar as condições de contacto utilizável, preparar **8 pilotos adicionais** com Nakagami m=3 e m=5, com/sem ARP pré-configurado, policies immediate/FIFO e run=1; sem apagar os resultados de m=1:

~~~bash
cd ~/COMOV/Project_B/COMOV_NS3_B
git pull
python3 scripts/test_p3_fading_severity.py
python3 scripts/run_p3_fading_severity.py ../../ns-3 --run 1 --skip-existing
~~~

Enviar só `out/p3/p3_fading_severity_run1_complete.zip`. Ver [protocolo m=3/5](docs/23_p3_fading_assoc_ack_e_severidade.md). Código C++ com esta alteração ainda exige compilação real no ns-3.48 local; GitHub CI verifica apenas estrutura e scripts.

## P3 — Três testes críticos com 10 runs emparelhadas

O ZIP `p3_fading_severity_run1_complete.zip` foi auditado (97/97 hashes). A 15 m/s, stop=0, **Nakagami m=5 com ARP dinâmico** entregou **1666 mensagens imediatas e 5412 FIFO**, ganho de **+3746 mensagens / +31,217 pp**, com goodput no prazo por segundo associado de 0,766/2,459 Mbit/s. A m=3 com ARP dinâmico houve **zero UDP em ambas as políticas**, pois as capturas mostram pedidos ARP sem respostas e sem IPv4; com ARP pré-configurado foram recebidas 1555/5028. O resultado m=3 com ligação falhada **não demonstra** equivalência entre FIFO e envio imediato. Ver [análise completa](docs/24_p3_fading_m5_e_dez_runs_paired.md).

Para obter uma conclusão com intervalos de confiança do **modelo ns-3**, repetir 10 vezes os três testes, mantendo a P2 sem alterações. O script executa 8 configurações/run: controlo immediate/FIFO, fading **m=5 com ARP dinâmico** immediate/FIFO, concorrência 2 Mbit/s immediate/FIFO e variantes FIFO com pacing 3 ms ou capacidade 2 MB. O P3 controlo é confrontado com o mesmo run da P2. Runs com zero UDP são **incluídas e assinaladas**, não removidas do resultado.

~~~bash
cd ~/COMOV/Project_B/COMOV_NS3_B
git pull
python3 scripts/test_p3_repeated_tests.py
python3 scripts/run_p3_repeated_tests.py ../../ns-3 --start-run 1 --end-run 10 --skip-existing
python3 scripts/pack_p3_repeated_tests.py --start-run 1 --end-run 10
~~~

Enviar apenas `out/p3/p3_repeated_runs1-10_complete.zip`, com os CSV/JSON dos 80 ensaios, sumários P2 de controlo, comparações emparelhadas, IC95%, PCAP pertinentes e manifest SHA-256. Os primeiros 8 resultados já foram feitos; restam **72 simulações**, sujeitas a compilação/teste no ns-3.48 local.
