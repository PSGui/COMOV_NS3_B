# P1 — Mobilidade contínua, associação Wi-Fi e UDP (ns-3.48)

**Estado:** implementação escrita; compilação e execução no WSL ainda pendentes. P0 já validou a implementação do modelo determinístico de propagação.

## Pergunta experimental

Durante a passagem do autocarro por um AP fixo, **quando** há associação Wi-Fi, quantas mensagens UDP são aceites pela socket e quantas chegam ao AP?

Não confundir sucesso no envio com receção, associação com serviço utilizável ou ausência de receção com perda PHY comprovada.

## Configuração inicial

| Parâmetro | Valor P1 | Origem |
|---|---|---|
| ns-3 / Wi-Fi | ns-3.48 / 802.11g, 2,412 GHz, canal 1 | P0 + escolha provisória |
| PHY | ERP-OFDM fixo 6 Mbit/s (`ErpOfdmRate6Mbps`); 20 dBm; Gtx=Grx=0 dB | corrigido após abort de validação no ns-3.48 |
| Propagação | log-distance, n=3, d0=1 m, ReferenceLoss=FSPL(2,412 GHz,1 m) | P0 |
| AP | (0,0,4) m | hipótese |
| Autocarro | ConstantVelocityMobilityModel, altura 2,5 m | movimento contínuo |
| Posição inicial | x(0)=-70v, x(70)=0 | por construção |
| Paragem | v=0 de t=70 até t=70+s; depois volta a v | aceleração instantânea (limitação) |
| Primeiro piloto | v=5 m/s; s=10 s | caso de referência |
| UDP | autocarro → AP, porta 9010, IPv4 10.8.0.0/24 | sem tráfego concorrente |
| Geração | 100 msg/s de 1000 bytes; 12000 IDs | B10 |
| Payload | 16 bytes ID+timestamp +984 bytes dados | mantém 1000 bytes UDP |
| Janela | [10,130) s; observação até 200 s | constante entre políticas |
| Prazo | 60 s desde geração | B10 |
| RNG | seed=1 e run=1 no piloto | outras runs só depois |

**Limitações:** sem fading, shadowing variável, obstáculos, aceleração real, tráfego exterior nem handover.

## Regra de envio imediato adotada

O P1 adota uma definição **estrita, sem buffer na aplicação**.

1. Cada mensagem é gerada no instante previsto, mesmo fora de cobertura.
2. Se a STA não estiver associada, há um descarte explícito na aplicação (no_association), sem chamar SendTo. Evita backlog oculto pré-associação nas filas IP/MAC.
3. Se estiver associada, a aplicação chama SendTo imediatamente e guarda o resultado.
4. O AP regista a primeira receção por ID e as duplicadas separadamente.

Quando SendTo aceita um datagrama, **a rede pode ainda manter esse datagrama em filas inferiores**, logo não temos prova de transmissão rádio nem de entrega. O P1 mede a diferença, mas não diagnostica todas as causas do insucesso PHY/MAC.

Esta opção para "sem buffer" é metodológica e deverá ser discutida com o docente se necessário. **Não deve ser alterada depois de ver os resultados sem registar a mudança.**

## CSV produzidos

Para o prefixo out/p1/v5_stop10_run1:

- _generated.csv: 12000 linhas, ID, instante, posição, distância, associação, retorno da socket e razão do descarte;
- _received.csv: ID, geração, receção, atraso, deadline e duplicação;
- _association.csv: eventos Assoc/DeAssoc efetivos e localização;
- _mobility.csv: 801 amostras de tempo (cada 0,25 s), distância, velocidade, associação e Pr calculado pelo modelo;
- _summary.csv: contadores, tempo associado, velocidade, paragem, seed/run;
- _analysis.json: relatório do verificador independente.

Contabilidade exigida:

~~~
N_generated = N_no_assoc + N_socket_rejected + N_socket_accepted
N_socket_accepted = N_unique_received + N_accepted_not_observed
N_unique_received = N_on_time + N_late
P_on_time = N_on_time / N_generated
~~~

A categoria accepted_not_observed **não é automaticamente uma perda física**; pode incluir esperas em filas, descarte em camadas inferiores ou não receção até ao fim da observação. O tempo associado também não é necessariamente tempo útil de contacto UDP.

## Execução no WSL

Após merge do PR:

~~~bash
cd ~/COMOV/Project_B/COMOV_NS3_B
git pull
bash scripts/run_p1.sh ../../ns-3 5 10
~~~

O script copia o código P1 para o scratch do simulador, executa-o e verifica todos os CSV. O modo require-contact é apenas um requisito do piloto: um cenário sem associação poderá ser uma execução válida em testes posteriores, mas não permite confirmar este piloto.

Criar gráficos:

~~~bash
python3 scripts/plot_p1.py --prefix out/p1/v5_stop10_run1
~~~

São criadas três figuras PNG (distância, associação e receções UDP) com eixo temporal comum, mais linhas verticais a marcar a paragem.

**Depois de confirmar o caso inicial**:

~~~bash
bash scripts/run_p1.sh ../../ns-3 15 10
bash scripts/run_p1.sh ../../ns-3 5 0
bash scripts/run_p1.sh ../../ns-3 5 30
~~~

Não começar ainda as 10 repetições e os IC95%. Primeiro validar eventos, tempos e métricas.

## Critérios mínimos para aprovar P1

1. C++ compila em ns-3.48 sem alterações locais não versionadas.
2. Há 12 000 mensagens e os IDs, tempos e posições são os previstos.
3. O autocarro desloca-se continuamente e permanece parado no intervalo escolhido.
4. Os eventos Assoc/DeAssoc surgem sem limites de cobertura hardcoded.
5. Há receções UDP identificáveis com atraso positivo.
6. Todos os contadores reconciliam e as duplicadas não contam duas vezes.
7. O denominador da entrega em 60 s é o número total gerado.
8. Os três gráficos permitem relacionar posição, associação e receções.

O ns-3 pode manter a associação durante um intervalo após perda de capacidade rádio, dependente de beacons e mecanismos MAC. **Não forçar desligamento por distância**. O programa P1 é a fonte versionada; a cópia em scratch não deve ser editada manualmente.

## Referências técnicas

- [ns-3.48 StaWifiMac: Assoc, DeAssoc e IsAssociated](https://fossies.org/dox/ns-3.48/sta-wifi-mac_8cc_source.html)
- [ns-3.48 ConstantVelocityMobilityModel](https://fossies.org/linux/privat/ns-3.48.tar.bz2/ns-3.48/src/mobility/model/constant-velocity-mobility-model.cc)
- [ns-3.48 UDP server receive callback](https://fossies.org/dox/ns-3.48/udp-echo-server_8cc_source.html)
- Worksheet B: B10 p. 12; método geral pp. 1–3.

## Incidente de integração P1 — primeira execução

Na primeira execução do utilizador (`bash scripts/run_p1.sh ../../ns-3 5 10`), o programa **compilou** mas abortou em t=46,959028 s. Diagnóstico confirmado no ns-3.48, `wifi-tx-vector.cc:529`: `OfdmRate6Mbps` (classe OFDM) não é modo de dados válido na banda de 2,4 GHz para o standard 802.11g. Correção: `DataMode` e `ControlMode` passam a `ErpOfdmRate6Mbps` (classe ERP-OFDM). O P0 anterior não encontrou o problema porque não enviou dados UDP. Não existem ainda resultados UDP P1 válidos. Após integrar a correção, recompilar e repetir; a mensagem `PASS` do validador e os CSV deverão ser enviados para revisão.
