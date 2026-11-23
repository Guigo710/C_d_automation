# 01: Esqueleto: login e "minha organização"

**What to build:** um usuário de uma organização entra com e-mail e senha e vê uma tela com o nome da sua organização e o seu papel. É a primeira fatia de ponta a ponta: SPA React/Vite em TypeScript, API FastAPI, PostgreSQL com RLS por organização, login pelo Supabase Auth (ADRs 0001 a 0003) e a base de testes da API que todos os tickets seguintes usam. A aplicação é empacotada em imagem Docker desde já (ADR 0004).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

> **Verificado (23/11/2026):** tipos, lint, build do frontend, teste de contrato e testes de API (`tests/test_acesso.py`) contra o PostgreSQL de teste passam.

- [ ] Existem organização e perfil de usuário (vínculo do usuário do Supabase Auth com organização, papel — administrador, coordenador ou vendedor — e status ativo); o token do usuário carrega `organizacao_id` e papel vindos do perfil, nunca do próprio usuário
- [ ] Toda tabela de negócio tem `organizacao_id` e política de RLS que restringe leitura e escrita à organização do token
- [ ] A API valida o token do Supabase; uma rota devolve a organização e o papel do usuário logado; usuário inativo ou sem perfil é recusado
- [ ] O frontend tem login com e-mail e senha, recuperação de senha por e-mail e a tela "minha organização"
- [ ] Tipos do frontend gerados a partir do OpenAPI da API; o build quebra se o contrato mudar
- [ ] Mapa único de permissões por papel, aplicado por rota, pronto para os próximos tickets
- [ ] Base de testes: PostgreSQL real com esquema, RLS e funções aplicados; tokens de teste assinados com segredo de teste; usuários de papéis diferentes em duas organizações
- [ ] Teste: usuário da organização A não lê dado da organização B nem quando a consulta da rota não filtra por organização (o RLS barra)
- [ ] Script para o administrador da plataforma criar uma organização e seus usuários sem tela
- [ ] Imagem Docker da API constrói e sobe localmente com a configuração por variáveis de ambiente
