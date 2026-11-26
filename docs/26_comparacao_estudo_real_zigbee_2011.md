# B10 — Comparação crítica com um estudo experimental Zigbee entre autocarros e paragens

**Fonte primária:** Razi Iqbal, Kenichi Yukimatsu e Tatsuya Ichikawa, *The Flexible Bus Systems Using Zigbee as a Communication Medium*, **International Journal of Online Engineering (iJOE)**, vol. 7, n.º 3, agosto de 2011, pp. 9–14. DOI: **10.3991/ijoe.v7i3.1579**. PDF de seis páginas facultado pelo grupo (capa corresponde à página 9 do periódico): https://doi.org/10.3991/ijoe.v7i3.1579

**Objetivo desta revisão:** identificar se o artigo constitui **trabalho relacionado baseado em medições reais**, com o qual podemos interpretar os resultados de simulação ns-3 (B10 P2/P3), sem confundir grandezas ou validar artificialmente um modelo de propagação.

## 1. O que o artigo realmente investiga

O artigo propõe um *Flexible Bus System* com ligação de curto alcance **Zigbee/XBee** entre autocarros e paragens (*Intelligent Bus Stops*), que por sua vez comunicam com um centro de controlo através da Internet. A informação trocada consiste em pequenos campos de identificação e operação (identidade de autocarro e paragem, decidir parar/não parar, número de passageiros, destino). Os autores referem que são **poucos bytes** de informação, não conteúdos volumosos. Ver secções II, V e figura 7 (pp. 9–11).

Na figura 9 (p. 12), o objetivo é **iniciar comunicação até 100 m** e **concluir a troca de controlo antes dos 50 m** da paragem, por motivo de segurança/decisão de travagem. Isto fundamenta a ideia de que existe uma **janela de contacto limitada por movimento e alcance rádio** — também central no nosso projeto. No nosso B10, porém, não há necessidade de receber uma instrução antes de uma distância de travagem: procuramos transferir datagramas durante o contacto e verificar entrega num prazo de **60 s**.

Os autores fazem **ensaios físicos com módulos MaxStream XBee Pro**, descritos na secção VI, e também usam simulações de itinerários de autocarros em 'Konno Simulator' para comparar tempos de espera/viagem (figuras 5 e 6). Não confundir essas simulações de gestão de transporte com medições rádio: **os gráficos de tempos de espera/viagem não são resultados comparáveis aos atrasos de pacotes UDP do nosso B10**.

## 2. Resultados experimentais reais de comunicação Zigbee

**Configuração reportada:** mensagem de tamanho máximo **7 bytes**, envio **uma vez por segundo**, distâncias entre módulos até **100 m**, colocação até cerca de **2 m** de altura, três condições de visibilidade/obstrução (figuras 9–12 e tabelas I–III, pp. 12–13). A descrição não demonstra uma campanha estatística grande nem um estudo isolado de velocidade de deslocação.

| Condição no artigo | Distância | Receções / tentativas | Taxa de sucesso observada | Taxa de insucesso observada |
|---|---:|---:|---:|---:|
| Estrada reta, linha de vista (LOS) | 100 m | **18 / 18** | **100,00%** | **0,00%** |
| Árvores, sem linha de vista | 100 m | **28 / 36** | **77,78%** | **22,22%** |
| Edifícios, sem linha de vista | 100 m | **6 / 18** | **33,33%** | **66,67%** |
| Edifícios, sem linha de vista | 80 m | **18 / 30** | **60,00%** | **40,00%** |
| Edifícios, sem linha de vista | 50 m | **24 / 30** | **80,00%** | **20,00%** |

Estes valores correspondem **exatamente às tentativas registadas** nas tabelas do artigo, e não a PDR end-to-end da aplicação B10. Os autores interpretam que mais obstrução e maior distância tornam a comunicação Zigbee mais difícil. A interpretação é fisicamente plausível, mas também muda a geometria entre ensaios: a tabela não fornece uma estimação controlada de expoente log-distance nem de parâmetros Nakagami para Wi-Fi.

**Ressalva documental importante:** a secção VII declara que a velocidade do autocarro e as condições meteorológicas não tiveram efeito significativo. Contudo, as tabelas I–III apresentadas descrevem *distância, obstrução e tentativas*, sem uma matriz de velocidade/meteo ou testes estatísticos visíveis. Portanto, **não usar essa afirmação isolada para contestar os efeitos de velocidade nas nossas simulações**. Os autores também fazem afirmações gerais sobre ausência de interferência de Wi-Fi/3G/Bluetooth sem mostrar medições detalhadas dessas interferências nas tabelas; não extrapolar.

## 3. Mapeamento com o nosso ns-3 COMOV B10

| Aspeto | Artigo de 2011 | Projeto B10 P2/P3 | Comparação defensável? |
|---|---|---|---|
| Arquitetura | Autocarro ↔ paragem com Zigbee; paragem ↔ centro de controlo | Autocarro ↔ RSU/AP com Wi-Fi 802.11g | **Sim, conceptual** (comunicação oportunista V2I em paragem) |
| Janela de contacto | Alcance de 100 m e decisão antes de 50 m | Cobertura/associação dependente da distância, velocidade 5/15 m/s, paragens 0/10/30 s | **Sim, conceptual**, não igualar raios de cobertura |
| Física e obstáculos | Medições reais LOS, árvores e edifícios | Propagação log-distance determinística e Nakagami m=1/3/5 não calibrado | **Sim, qualitativo**: o canal condiciona o sucesso; não equiparar obstáculos ao m |
| Protocolo | Zigbee/XBee | Wi-Fi IEEE 802.11g, ERP-OFDM 6 Mbit/s, associação e ARP | **Não**, para taxas de erro/debito numéricos |
| Carga útil | Até 7 B, 1 transmissão/s | UDP 1000 B, 100 transmissões geradas/s, 12000/execução | **Não**, os denominadores e congestionamento diferem |
| Objetivo da entrega | Pequeno controlo operacional antes de distância de segurança | Volume útil no AP, entrega ≤60 s, goodput útil por segundo associado | **Não**, metas e métricas diferentes |
| Armazenamento | Informação pode ser retransmitida/paragem serve de intermediária; **não testa FIFO no autocarro** | Compara app immediate, que descarta sem associação, contra buffer FIFO 4/2 MB com expiração | **A nossa hipótese não foi testada no artigo** |

### Resultados B10 que podem ser discutidos em diálogo com o artigo (NÃO na mesma escala estatística)

Na baseline P2 (15 m/s, paragem 0 s, dez runs), FIFO entregou **46,129%** das 12000 mensagens geradas, envio imediato **12,804%**, ganho **+33,325 pp**, IC95% **[33,319; 33,331]** condicionado ao modelo. Na P3 com outra STA a oferecer UDP 2 Mbit/s, os valores foram **35,593%** FIFO vs **12,636%** imediato, ganho **+22,957 pp**. Sob Nakagami m=5/ARP dinâmico, **7/10 runs** tiveram zero UDP recebido em ambas as políticas; nas três runs funcionais FIFO entregou mais mensagens, mas o ganho global apresentou IC95% Student-t **[−1,409; 19,920] pp**. Os sete zeros foram associados a falhas de contacto útil/ARP; **não significam uma probabilidade de perda de 70% dos datagramas no canal**.

O artigo mostra que até **pequenas mensagens** sofrem com condições rádio adversas numa paragem; o B10 acrescenta a distinção entre **(1) existir conectividade útil** e **(2) aproveitar esse contacto para escoar muitos dados armazenados**. Essa é uma conexão válida entre a evidência de campo e a nossa experiência de simulação.

## 4. Comparações que devemos explicitamente rejeitar

1. **Não colocar 66,67% de 'perda por edifícios' ao lado de 7/10 runs sem UDP** como se fossem a mesma medida. No artigo, 66,67% é fração de *pacotes Zigbee enviados e não recebidos* em 18 tentativas a 100 m; na P3 são *passagens inteiras sem entrega end-to-end de UDP*, podendo falhar já em associação/ARP. As amostras e mecanismos são distintos.
2. **Não validar o alcance de Wi-Fi por 'Zigbee também funciona a 100 m'.** Transceptores, potência, sensibilidade, modulação, obstrução e limiares de deteção diferem.
3. **Não afirmar que Nakagami m=5 corresponde a árvores ou edifícios medidos pelos autores.** Não existe calibração comum de distribuições, alturas e geometria.
4. **Não comparar atraso médio de pacotes (até dezenas de segundos pela FIFO) com tempo de espera dos passageiros nas figuras 5–6.** São grandezas distintas.
5. **Não usar as pequenas amostras físicas para afirmar universalmente que LOS oferece 0% perdas ou que Zigbee não depende de velocidade.** Resultados limitados ao procedimento reportado.

## 5. Formulação recomendada para revisão bibliográfica / discussão

> Iqbal et al. (2011) investigaram experimentalmente a comunicação sem fios entre autocarros e paragens através de Zigbee, demonstrando que a receção de mensagens curtas depende fortemente da geometria e dos obstáculos. A 100 m, observaram receção de 18/18 mensagens em linha de vista, 28/36 com árvores e 6/18 com edifícios. Embora estes valores não sejam diretamente comparáveis com as métricas do presente estudo, baseado em Wi-Fi e datagramas UDP de 1000 bytes, sustentam a necessidade de avaliar a comunicação autocarro–infraestrutura para além de uma hipótese de cobertura ideal. O nosso B10 complementa esse enquadramento ao estudar não apenas a possibilidade de estabelecer contacto, mas também o aproveitamento de janelas intermitentes para descarregar mensagens previamente armazenadas. Os ensaios P3 mostram que a FIFO melhora a entrega quando há contacto útil e capacidade suficiente, mas não consegue evitar falhas de estabelecimento de comunicação e pode sofrer limitações de débito, memória e atraso.

## 6. Recomendação de apresentação

**Um slide de trabalhos relacionados:** colunas 'Zigbee: medição em campo' e 'B10: simulação ns-3', citando as tabelas I–III do artigo; terminar com uma linha separadora: '**Comparação de mecanismos, não de taxas diretamente equivalentes**'. Incluir os nossos resultados P2/P3 num slide seguinte, com as unidades/denominadores explícitos. É desnecessário criar novas simulações apenas para fazer os valores do artigo coincidirem.

### Referência bibliográfica

[1] R. Iqbal, K. Yukimatsu, and T. Ichikawa, “The Flexible Bus Systems Using Zigbee as a Communication Medium,” *International Journal of Online Engineering*, vol. 7, no. 3, pp. 9–14, Aug. 2011, doi: **10.3991/ijoe.v7i3.1579**.
