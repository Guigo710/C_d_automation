# Login pelo Supabase Auth

O Plano v2 previa um login próprio (tabela de usuários com senha argon2, MFA, bloqueio e expiração de sessão). Trocamos pelo Supabase Auth, porque o banco já é Supabase (ADR 0002) e ele entrega pronto convite e recuperação por e-mail, login com Google ou Microsoft, MFA por aplicativo e um token que o RLS lê direto. O token carrega `organizacao_id` e o papel do usuário; o FastAPI só valida esse token, e os papéis e regras de permissão continuam na nossa API e no banco. Isso economiza de 2 a 3 semanas da v0.

**Consequences**

- O login fica preso ao Supabase: sair dele significa migrar usuários e sessões, não só o banco.
- Papéis (administrador, coordenador, vendedor) e a organização do usuário são definidos por nós, não pelo Supabase; o Supabase só autentica.
