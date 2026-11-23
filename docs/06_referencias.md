# Referências verificáveis e ligação às decisões

## Requisitos do projeto e teoria da unidade curricular

- *Worksheet B*, COMOV 2026/27, secções 1–6, B10 na p. 12. Fonte da matriz de 12 configurações, contabilidade, IC95%, milestones e entregáveis.
- *Comov_03-RF_communications_i.pdf*: perdas de propagação, lei de Friis e potência recebida (pp. 4–8).
- *Comov_03-RF_communications_ii.pdf*: log-distance, sensibilidade, ruído, SNR e SINR (pp. 1, 6–7).
- *Comov_03-RF_communications_iii(1).pdf*: Doppler, tempo de coerência, link budget (pp. 1, 3–5).
- *Comov_03-RF_communications_iv(1).pdf*: QoS, percentis, ECDF e apresentação estatística (pp. 1–3).

Os PDFs são documentação de aula fornecida pelo grupo; **não** foram adicionados ao GitHub para evitar partilha involuntária de materiais da disciplina.

## Estudos científicos (artigos publicados)

1. García et al. (2016), **“Systematic Development of Intelligent Systems for Public Road Transport”**, *Sensors*, 16(7), 1104, DOI [10.3390/s16071104](https://doi.org/10.3390/s16071104). Aborda transferência de dados autocarro/infraestrutura em paragens; reporta dificuldades práticas com interrupções de ligação. **Não é um artigo dedicado à comparação FIFO vs envio imediato**.
2. Eriksson, Balakrishnan e Madden (2008), **“Cabernet: Vehicular Content Delivery Using WiFi”**, *ACM MobiCom*, DOI [10.1145/1409944.1409968](https://doi.org/10.1145/1409944.1409968). Mostra a importância do estabelecimento de ligação em contactos curtos.
3. Teixeira, Meireles e Aguiar (2024), **“Wi-Fi throughput estimation and forecasting for vehicle-to-infrastructure communication”**, *Computer Communications*, 214, DOI [10.1016/j.comcom.2023.12.005](https://doi.org/10.1016/j.comcom.2023.12.005). Fundamenta previsões de capacidade/throughput V2I e comparação teoria/observação.
4. Acer et al. (2012), **“Timely Data Delivery in a Realistic Bus Network”**, *IEEE Transactions on Vehicular Technology*, DOI [10.1109/TVT.2011.2179072](https://doi.org/10.1109/TVT.2011.2179072). Discute *store-carry-forward* em redes de autocarros; arquitetura diferente do nosso único AP.

**Comparação mais próxima proposta:** García et al. quanto ao contexto paragem/transferência; Acer et al. quanto à motivação para armazenar. Em ambos os casos, salientar diferenças no modelo e métricas; não atribuir-lhes as nossas decisões de 4 MB, 6 Mbit/s, expoente 3 ou prazo 60 s.

## Documentação do simulador

- [ns-3 Wi-Fi user documentation](https://www2.nsnam.org/docs/models/html/wifi-user.html): configuração infraestrutura, canal e modos PHY.
- [ns-3 Wi-Fi design documentation](https://github.com/nsnam/ns-3-dev-git/blob/master/src/wifi/doc/source/wifi-design.rst): associação e traces `Assoc`/`DeAssoc`; verificar na versão instalada.
- [ns-3 propagation models](https://www2.nsnam.org/docs/models/html/propagation.html): Friis e log-distance, referência e expoente.
- [ns-3 `wifi-simple-infra.cc`](https://gitlab.com/nsnam/ns-3-dev/-/blob/master/examples/wireless/wifi-simple-infra.cc): **ponto de partida**, mas utiliza `FixedRssLossModel` e deve ser adaptado à distância.

**Nota de rigor:** características do ns-3 dependem da versão. A versão exata e funcionalidades efetivamente instrumentadas devem ser fixadas e verificadas antes da M2.
