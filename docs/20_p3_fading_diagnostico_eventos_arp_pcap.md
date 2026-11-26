# B10 P3 — Diagnóstico do piloto fading e correção da auditoria

**Contexto real:** o grupo compilou P3 no ns-3.48 e o cenário reference reproduziu exatamente P2 a v=15 m/s, stop=0, run=1: immediate 1533/12000 recebidos, FIFO 5530/12000; 16,2571 s de associação.

**Problema observado em `fading immediate`:** 12000 geradas; 1829 datagramas aceites pela socket; **zero receções UDP no AP**, `assoc_events=2`, `deassoc_events=5` no log inicial. A revisão P2 rejeitou a sequência como associação/desassociação mal emparelhadas e interrompeu os oito pilotos. Isto não é evidência científica de que Nakagami elimina o ganho. A configuração Nakagami m=1 deveria permitir receções com probabilidade positiva; há que identificar a razão das zero entregas.

## Mudanças de diagnóstico (não alteram a baseline P2)

- `src/b10-p3-stress.cc`: todos os callbacks brutos `Assoc` e `DeAssoc` ficam preservados em `*_association_raw.csv`, incluindo `already_open` e `sta_is_associated`. O CSV `association.csv` regista somente transições emparelhadas de associação; o resumo indica quantos callbacks extra foram recebidos (`ignored_assoc_callbacks`, `ignored_deassoc_callbacks`). Não se apagam os callbacks extra: são observáveis no CSV bruto.
- Em modo fading, ativa-se PCAP nos dois rádios, guardando `*_pcap_ap*.pcap` e `*_pcap_bus*.pcap`; isto permitirá distinguir tramas de gestão/ARP/dados na ligação. Não inferir a causa a partir de `SendTo=1000`.
- `scripts/review_p3.py`: mantém TODAS as validações estritas da contabilidade de P2, reconcilia os callbacks brutos e os intervalos válidos, acrescenta avisos de qualidade aos JSON. A revisão P2 original não é modificada.
- `scripts/run_p3_pilots.py`: distingue pilotos com associação mas zero UDP recebidos de pilotos sem avisos; prossegue recolhendo as oito experiências para permitir análise de diagnóstico; recusa reutilizar resultados antigos sem CSV bruto ou PCAP obrigatórios.
- `scripts/pack_p3_results.py`: inclui os callbacks extra, os PCAP e o ficheiro de avisos em um ZIP, para análise única. Se não existir a evidência necessária, falha explicitamente.

## Comandos depois de integrar o PR no GitHub

```bash
cd ~/COMOV/Project_B/COMOV_NS3_B
git pull
python3 scripts/test_p3_pilots.py
python3 scripts/run_p3_pilots.py ../../ns-3 --speed 15 --stop 0 --run 1 --skip-existing
python3 scripts/pack_p3_results.py --speed 15 --stop 0 --run 1
```

**Enviar um único ficheiro:** `out/p3/p3_pilots_v15_stop0_run1_complete.zip`. Inclui os oito conjuntos CSV, logs brutos de associação e capturas Wi-Fi para o fading. Se voltar a parar antes do ZIP, enviar o erro integral.

**Critério de aceitação:** P3 reference deve reproduzir P2 e os validadores de contabilidade devem passar. Zero receções UDP com associação em fading continua a ser **anomalia a investigar**, mesmo que a contabilidade seja matematicamente consistente. Comparar ganhos científicos apenas depois de compreender as capturas e causas de falha.
