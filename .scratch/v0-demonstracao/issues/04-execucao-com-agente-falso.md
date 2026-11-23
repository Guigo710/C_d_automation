# 04: Execução da prospecção com o agente falso (M1)

**What to build:** o coordenador manda executar a prospecção de uma campanha e volta ao trabalho; um job entra na fila no PostgreSQL, o worker no mesmo processo da API (ADR 0004) chama o agente de prospecção, e a plataforma grava empresas, evidências e candidatos. A tela mostra o andamento e a lista de candidatos. Este ticket fixa o contrato do agente de prospecção da spec e entrega o agente falso, que devolve candidatos de um arquivo de exemplo; o agente real será escrito à parte e trocado por configuração.

**Blocked by:** 03 (Campanhas)

**Status:** ready-for-agent

> **Estado (23/11/2026):** código commitado; tipos, lint, build e o agente falso (rodado isoladamente) passam. Testes de API (`tests/test_execucao.py`) passam contra o PostgreSQL de teste (23/11/2026).

- [ ] Contrato do agente de prospecção: recebe a fotografia da campanha (organização, municípios IBGE, segmentos e CNAEs, limite de empresas, saldo do teto) e devolve candidatos de forma incremental, cada um com CNPJ, razão social, nome fantasia, endereço, município, segmento, contatos e site com fonte, sinais comerciais, evidências (fonte, link, data) e custo incremental
- [ ] Agente falso no mesmo contrato, lendo um arquivo de exemplo com empresas realistas; o agente usado é escolhido por configuração
- [ ] Fila de jobs em tabela, atrás de uma interface própria, com estados na fila, executando, concluída, parcial e falhou, contagens, custo, erro e última atividade
- [ ] Iniciar a execução devolve o id do job na hora; a tela acompanha o progresso por consulta periódica
- [ ] Plataforma grava empresa, evidências e candidato com status coletado; deduplica por CNPJ dentro da campanha e entre campanhas ativas da organização
- [ ] Tela da campanha com andamento da execução e lista paginada de candidatos com seus dados e evidências
- [ ] Só coordenador inicia execução (testado)
- [ ] Teste: executar duas vezes a mesma campanha não duplica candidatos
