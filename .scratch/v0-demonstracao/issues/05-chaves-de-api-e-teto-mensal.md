# 05: Chaves de API e teto mensal

**What to build:** o administrador da organização cadastra, numa tela de configuração, as chaves de API dos fornecedores (Claude e fontes de dados) e o teto de gasto mensal, e vê quanto já foi gasto no mês. Cada organização paga os próprios fornecedores (ADR 0001).

**Blocked by:** 01 (Esqueleto: login e "minha organização")

**Status:** ready-for-agent

- [ ] Chaves guardadas cifradas pela aplicação, por organização e por fornecedor
- [ ] Depois de salva, a chave nunca volta inteira pela API, só os últimos caracteres (testado)
- [ ] Teto de gasto mensal configurável; gasto do mês calculado a partir do custo das execuções
- [ ] Tela de configuração com chaves, teto e gasto do mês
- [ ] Só administrador da organização lê e altera (testado)
- [ ] Os serviços internos obtêm a chave da organização por uma interface única, para os agentes usarem
