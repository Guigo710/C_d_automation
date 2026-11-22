# 02: Registro de auditoria imutável

**What to build:** as ações relevantes de uma organização ficam num registro que o próprio banco não deixa alterar nem apagar. Este ticket cria o registro e grava o primeiro evento, o login; os tickets seguintes acrescentam os seus eventos (exportação, aprovação, promoção, troca de responsável).

**Blocked by:** 01 (Esqueleto: login e "minha organização")

**Status:** ready-for-agent

- [ ] Registro de auditoria por organização com quem, o quê, sobre qual recurso e quando
- [ ] O banco recusa UPDATE e DELETE no registro (testado)
- [ ] Login gera um evento no registro
- [ ] Administrador da organização lista os eventos da própria organização pela API; outros papéis não
- [ ] Teste: eventos de uma organização não aparecem para outra
