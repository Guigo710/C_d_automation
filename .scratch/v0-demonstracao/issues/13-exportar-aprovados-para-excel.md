# 13: Exportar aprovados para Excel

**What to build:** o coordenador exporta os aprovados de uma campanha para um arquivo XLSX, para levar a uma reunião. Vendedores não exportam, para que a carteira não saia junto com quem sai da empresa.

**Blocked by:** 02 (Registro de auditoria imutável), 08 (Kanban de triagem)

**Status:** ready-for-agent

> **Pendente (22/11/2026):** código commitado; tipos, lint e build passam. Na v0 o arquivo é baixado direto, sem bucket nem link que expira; contatos ficam fora da planilha. Testes de API (`tests/test_exportacao.py`) aguardam o PostgreSQL de teste (Docker).

- [ ] Botão de exportar aprovados na tela da campanha, só para coordenador
- [ ] Arquivo XLSX gerado sob demanda a partir do banco, com os dados e notas dos aprovados
- [ ] Vendedor recebe recusa da API ao tentar exportar (testado)
- [ ] Cada exportação gera evento de auditoria
