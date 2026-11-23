# 09: Promoção e ficha de abordagem (M2, prévia)

**What to build:** o coordenador marca aprovados e clica "subir para operação"; as empresas entram na campanha sem responsável, numa única transação que não duplica nada mesmo com clique repetido. Em seguida, um job gera pela IA a ficha de abordagem de cada empresa, e a tela mostra "ficha em preparo" até ela ficar pronta. Cada empresa ganha um histórico. Com este ticket, a prévia para a Destak está pronta.

**Blocked by:** 08 (Kanban de triagem)

**Status:** ready-for-agent

> **Estado (23/11/2026):** código commitado; tipos, lint e build passam. Testes de API (`tests/test_promocao.py`) passam contra o PostgreSQL de teste (23/11/2026). A ficha pela Claude API real ainda não foi exercitada.

- [ ] Promoção exige chave de idempotência por clique; repetir o lote ou o clique não cria empresas duplicadas (testado)
- [ ] Promoção ignora clientes atuais e empresas na lista de bloqueio (testado)
- [ ] Empresas promovidas entram sem responsável
- [ ] Ficha de abordagem gerada pela IA a partir só de fatos com evidência; "ficha em preparo" enquanto o job não termina
- [ ] Histórico da empresa registra aprovação e promoção, com quem e quando
- [ ] Promoção gera evento de auditoria
- [ ] Tela de empresas da campanha para o coordenador, com ficha e histórico
