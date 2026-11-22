# 03: Campanhas

**What to build:** o coordenador cria, edita e lista campanhas da sua organização, escolhendo municípios, segmentos do catálogo de segmentos, tiers-alvo, limite de empresas, teto de gasto da campanha e os vendedores que participam. O catálogo de segmentos e o restante da configuração da organização (perfil ideal, pesos e cortes, municípios com rota, clientes atuais, lista de bloqueio) são semeados pelo administrador da plataforma, sem tela (ADR 0005).

**Blocked by:** 01 (Esqueleto: login e "minha organização")

**Status:** ready-for-agent

> **Pendente (22/11/2026):** código commitado; tipos, lint e build passam. Testes de API (`tests/test_campanhas.py`) aguardam o PostgreSQL de teste (Docker).

- [ ] Configuração da organização versionada, com catálogo de segmentos (segmento e CNAEs), perfil ideal, pesos e cortes (padrão 40/25/20/15; A ≥ 80, B ≥ 60, C ≥ 40), municípios com rota e atendidos sem rota, clientes atuais e lista de bloqueio, semeada por script com dados de exemplo da Destak
- [ ] Coordenador cria e edita campanha com municípios (código IBGE), segmentos do catálogo, tiers-alvo, limite de empresas, teto de gasto e vendedores participantes
- [ ] A API recusa segmento fora do catálogo da organização
- [ ] Campanha tem status rascunho, ativa, pausada ou encerrada
- [ ] Telas de lista e de criação/edição de campanha
- [ ] Vendedor não cria nem edita campanha (testado pela API)
- [ ] Teste: campanhas de uma organização não aparecem para outra
