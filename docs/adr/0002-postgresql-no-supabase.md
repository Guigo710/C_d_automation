# PostgreSQL no Supabase, com RLS por organização

Uma card antiga do Notion definia MySQL, mas escolhemos PostgreSQL gerenciado no Supabase, região São Paulo. O motivo principal é o Row Level Security: como a plataforma vai atender várias organizações (ADR 0001), o próprio banco recusa ler ou gravar dados de outra organização, mesmo que o código esqueça o filtro de `organizacao_id`. O MySQL não tem equivalente. Também pesam a busca aproximada de nomes (pg_trgm) para casar CNPJ com loja, o índice único parcial e `UPDATE … RETURNING`, todos usados nas regras de triagem e de assumir. O modelo de 17 tabelas do Plano v2 já foi testado em PostgreSQL 16.

**Consequences**

- Os dados ficam no Brasil (sa-east-1), com backup diário do fornecedor.
- Na v0 de demonstração usamos o plano gratuito do Supabase; o Pro entra quando a Destak assinar.
