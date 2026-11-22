# 08: Kanban de triagem

**What to build:** o coordenador tria os candidatos de uma campanha num kanban com colunas pendentes, aprovados e recusados, abre cada candidato numa gaveta lateral com dados, notas, justificativas, evidências e lacunas, aprova em lote, recusa com motivo, troca o tier com justificativa e restaura recusas sugeridas.

**Blocked by:** 02 (Registro de auditoria imutável), 07 (Qualificação: exclusões, notas e tier)

**Status:** ready-for-agent

- [ ] Kanban com pendentes, aprovados e recusados (recusas por regra marcadas como "sugerido"), com filtro e ordenação por tier, nota e segmento
- [ ] Gaveta lateral do candidato com todos os dados, notas, justificativa da IA, evidências, lacunas e selo de baixa confiança
- [ ] Aprovação em lote
- [ ] Recusa exige motivo da lista (fora do perfil, CNPJ inativo, fora da região, dados incompletos, já é cliente, duplicado, opt-out); sem motivo, a API recusa (testado)
- [ ] Troca de tier exige justificativa; sem justificativa, a API recusa (testado)
- [ ] Coordenador restaura uma recusa sugerida
- [ ] Aprovações e recusas registram quem decidiu e quando; aprovação gera evento de auditoria
- [ ] Vendedor não tria (testado)
