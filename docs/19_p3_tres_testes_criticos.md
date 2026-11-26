# B10 / P3 — Três experiências para desafiar a vantagem da FIFO

**Aim:** Find out whether storing data on the bus makes better use of Wi-Fi contact at a stop.

Esta fase é separada da matriz validada P2 (120 simulações). O executável novo é src/b10-p3-stress.cc, com logs exclusivamente em out/p3/.

## Controlo e critério científico

Cada cenário mantém 15 m/s, 0 s de paragem, 12000 mensagens UDP de 1000 B, deadline 60 s, PHY 802.11g ERP-OFDM 6 Mbit/s, potência de 20 dBm e expoente log-distance 3. FIFO de referência: 4 MB e pacing 2 ms. Seed=1/run=1 no piloto.

O P3 executa antes de tudo duas configurações reference (immediate/FIFO) e exige que reproduzam exatamente as mensagens recebidas e a duração associada da P2, com o mesmo run. Se não reproduzir, o script falha. A taxa de entrega e o goodput por segundo associado, NÃO a quantidade aceite por SendTo, respondem ao aim.

## Experiência A — Fading do canal

Intervenção: encadear NakagamiPropagationLossModel com m0=m1=m2=1 (caso Rayleigh) ao log-distance. Testar immediate e FIFO em separado. Procura-se saber se a vantagem permanece quando a qualidade rádio varia entre tramas. É um teste de fading rápido, não de shadowing urbano correlacionado. A potência no mobility.csv continua a prever só o log-distance para que a instrumentação NÃO consuma amostras aleatórias da PHY.

## Experiência B — Tráfego concorrente

Intervenção: nova STA estática a 10 m do AP, na mesma rede/canal, com UDP de aplicação oferecido a 2 Mbit/s, pacote de 1000 B, ativo entre t=5 e t=135 s, destino AP porta 9011. O tráfego de B10 mantém porta 9010. Os campos background_rx_packets e background_rx_bytes comprovam que o AP recebeu tráfego da concorrente. Testar immediate e FIFO.

## Experiência C — Limites do armazenamento

Sem alterar o canal nem adicionar concorrente: testar FIFO com pacing 3 ms e 4 MB; testar, separadamente, FIFO com pacing 2 ms e apenas 2 MB. Comparar ambos à FIFO original de 2 ms/4 MB, reutilizando o immediate de referência. Nunca alterar capacidade e pacing simultaneamente no mesmo ensaio inicial.

## Oito execuções iniciais

| Nº | Modo | Política | Pacing | Buffer |
|---:|---|---|---:|---:|
| 1 | reference | immediate | 2 ms | 4 MB |
| 2 | reference | fifo | 2 ms | 4 MB |
| 3 | fading | immediate | 2 ms | 4 MB |
| 4 | fading | fifo | 2 ms | 4 MB |
| 5 | contention | immediate | 2 ms | 4 MB |
| 6 | contention | fifo | 2 ms | 4 MB |
| 7 | reference | fifo | 3 ms | 4 MB |
| 8 | reference | fifo | 2 ms | 2 MB |

## Comandos no WSL após integração do PR

```bash
cd ~/COMOV/Project_B/COMOV_NS3_B
git pull
python3 scripts/test_p3_pilots.py
python3 scripts/run_p3_pilots.py ../../ns-3 --speed 15 --stop 0 --run 1 --skip-existing
python3 scripts/pack_p3_results.py --speed 15 --stop 0 --run 1
```

Enviar UM ficheiro: out/p3/p3_pilots_v15_stop0_run1_complete.zip. Inclui resultados agregados, 7 CSV + analysis.json de cada execução, os resumos P2 anteriores e manifest SHA-256. Se houver erro ao compilar C++, enviar o erro integral: o P3 ainda não foi compilado pelo GitHub Actions.

## Resultados que se pretende obter

| Experiência | Pergunta | Medidas prioritárias |
|---|---|---|
| Controlo | P3 reproduz a P2 sem stress? | Entregues, duração associada, descartes |
| A — fading | FIFO continua útil com receção variável? | Receção em 60 s, tempo de contacto, goodput, atraso |
| B — concorrência | FIFO consegue descarregar quando Wi-Fi é partilhado? | Entregas B10, receções da STA concorrente, perdas |
| C — limites | Pacing/capacidade degradam a entrega? | Overflow, expirações, entrega e atraso |

Uma run é um PILOTO, sem inferência estatística. Se o mecanismo for válido, repetir os casos por run=2..10 antes de relatar IC95%. Não misturar as 120 runs da matriz P2 com modelos estocásticos diferentes. O goodput útil é payload recebido por segundo associado, não airtime/ocupação PHY.
