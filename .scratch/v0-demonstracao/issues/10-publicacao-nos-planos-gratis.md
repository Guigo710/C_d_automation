# 10: Publicação nos planos grátis

**What to build:** a v0 fica no ar para a prévia: banco e login no Supabase (região São Paulo, plano grátis), API no Render grátis e frontend na Vercel grátis, todos publicando a partir do repositório no GitHub (ADRs 0002 e 0004). Precisa de contas e cartão criados por uma pessoa, por isso é `ready-for-human`; um agente pode preparar a configuração e um assistente passo a passo.

**Blocked by:** 01 (Esqueleto: login e "minha organização")

**Status:** ready-for-human

- [ ] Projeto no Supabase em São Paulo com esquema, RLS e funções aplicados por migração
- [ ] Hook do Supabase Auth que coloca `organizacao_id` e papel no token a partir do perfil
- [ ] API publicada no Render a partir da imagem Docker, com variáveis de ambiente configuradas e chave de cifragem das chaves de API definida
- [ ] Frontend publicado na Vercel apontando para a API
- [ ] Créditos da Claude API comprados e conta de faturamento do Google criada (as chaves são cadastradas pela tela do ticket 05)
- [ ] Organização Destak e usuários de demonstração criados pelo script do ticket 01
- [ ] Roteiro curto: abrir o sistema alguns minutos antes da demo, porque o Render grátis dorme
