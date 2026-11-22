# Uma organização hoje, preparado para SaaS depois

A Commercial Department Automation começa atendendo só a Destak, mas o objetivo é virar um SaaS por assinatura para outras empresas. Decidimos construir para um único cliente, sem fechar a porta para os próximos: toda tabela de dados de negócio tem `organizacao_id` desde o primeiro dia, toda consulta filtra por ela, e nada específico da Destak (segmentos, CNAEs, tiers, municípios, rotas, marca) fica no código; tudo isso é configuração da organização. Separar os dados por organização depois de o sistema estar pronto seria uma reescrita; fazer agora custa uma coluna e um filtro.

**Considered Options**

- **Sistema exclusivo da Destak**: mais simples, mas cada novo cliente viraria outro projeto.
- **SaaS completo desde a v0**: cadastro aberto, planos e cobrança automática atrasariam a demonstração em semanas, antes de existir um segundo cliente.

**Consequences**

- Cadastro aberto, gestão de planos e cobrança automática ficam fora até o segundo cliente; até lá, cada organização é criada à mão pelo administrador da plataforma.
- A relação com a Destak é uma assinatura (licença de uso), não a venda do sistema, para que o software continue nosso e possa ser oferecido a outras empresas.
- As chaves das APIs (Claude, Google, Brave) e o teto de gasto são configurados por organização dentro da plataforma, para que cada organização pague os próprios fornecedores.
