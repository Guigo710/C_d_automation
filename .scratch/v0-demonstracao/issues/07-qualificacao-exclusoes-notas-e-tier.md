# 07: Qualificação: exclusões, notas e tier (Agente 2)

**What to build:** depois da prospecção, cada candidato coletado é qualificado: exclusões por regra viram recusas sugeridas, as notas de geografia e de qualidade dos dados são calculadas por regra, a Claude dá as notas de aderência e potencial com justificativa e evidências, e o código calcula o total e o tier. O candidato passa a pendente e a lista de candidatos mostra notas e tier.

**Blocked by:** 04 (Execução da prospecção com o agente falso), 05 (Chaves de API e teto mensal)

**Status:** ready-for-agent

> **Pendente (22/11/2026):** código commitado; tipos, lint, build e as regras com o cliente de IA falso (rodadas isoladamente) passam. Validação de MX do e-mail não implementada (só sintaxe e domínio de contabilidade). Testes de API (`tests/test_qualificacao.py`) aguardam o PostgreSQL de teste (Docker). A chamada real à Claude API ainda não foi exercitada.

- [ ] Interface única de cliente de IA com implementação para a Claude API (Claude Haiku 5.5), usando a chave da organização; versão falsa determinística para testes
- [ ] Saída estruturada validada antes de gravar; resposta fora do esquema ou que cite evidência inexistente é reenviada uma vez e, na segunda falha, o candidato vai para revisão com o motivo
- [ ] Cache de respostas por hash (modelo, versão do prompt, entrada); checagem do teto antes de cada chamada; no máximo 2 novas tentativas e timeout de 60 segundos
- [ ] Exclusões por regra (CNPJ inativo, fora da região, já é cliente, duplicado, opt-out) geram recusa com etiqueta "sugerido"
- [ ] Validação de contato: sintaxe e domínio de e-mail; telefone com DDD válido
- [ ] Geografia (100 com rota, 60 atendido sem rota, 0 fora) e qualidade dos dados (30/30/20/20) por regra
- [ ] Aderência e potencial pela IA, baseadas no perfil ideal da organização; confiança abaixo de 0,6 marca "baixa confiança"
- [ ] Total e tier pelos pesos e cortes da organização; total abaixo do corte de C sugere recusa por fora do perfil
- [ ] Candidato pendente guarda notas, tier sugerido, motivos, lacunas, modelo, versão do prompt e versão das regras
- [ ] Teste: cálculo de total e tier com pesos e cortes da organização; mudar as regras não altera candidatos já qualificados
- [ ] Teste: cada exclusão gera o motivo sugerido certo
