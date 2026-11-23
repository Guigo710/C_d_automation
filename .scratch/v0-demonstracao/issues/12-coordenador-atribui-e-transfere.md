# 12: Coordenador atribui e transfere

**What to build:** o coordenador atribui uma empresa da campanha direto a um vendedor participante, sem esperar alguém assumir, e transfere uma empresa de um vendedor para outro. Cada troca fica no histórico da empresa e na auditoria.

**Blocked by:** 11 (Vendedor assume, com contato oculto)

**Status:** ready-for-agent

> **Estado (23/11/2026):** código commitado; tipos, lint e build passam. Testes de API (`tests/test_atribuicao.py`) passam contra o PostgreSQL de teste (23/11/2026).

- [ ] Coordenador atribui empresa sem responsável a um vendedor membro da campanha
- [ ] Coordenador transfere empresa entre vendedores membros da campanha
- [ ] A API recusa atribuir ou transferir para quem não é membro da campanha
- [ ] Vendedor não atribui nem transfere (testado)
- [ ] Cada troca registra no histórico (de quem, para quem, por quem, quando) e na auditoria
- [ ] Na tela do coordenador, ações de atribuir e transferir e o histórico visível na empresa
