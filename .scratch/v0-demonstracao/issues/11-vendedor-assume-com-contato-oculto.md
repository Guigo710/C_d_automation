# 11: Vendedor assume, com contato oculto (M3)

**What to build:** o vendedor vê as empresas aprovadas das campanhas de que participa, separadas em disponíveis e minhas, com nome, segmento, município, tier e ficha. Ao assumir uma empresa, passa a ver o contato dela; até lá, telefone, e-mail e nome do contato ficam ocultos, inclusive na API. Se dois vendedores assumirem ao mesmo tempo, só um fica com a empresa.

**Blocked by:** 09 (Promoção e ficha de abordagem)

**Status:** ready-for-agent

- [ ] Vendedor vê só empresas das campanhas de que é membro; filtro de escopo aplicado no SQL
- [ ] Contato mascarado pela API para quem não é coordenador nem responsável (testado)
- [ ] Assumir com "primeiro a assumir vence" garantido pelo banco; o segundo recebe aviso claro (testado com duas tentativas concorrentes)
- [ ] Empresa de outro vendedor responde "não encontrada" (testado)
- [ ] Assumir registra no histórico da empresa e gera evento de auditoria de troca de responsável
- [ ] Telas do vendedor: disponíveis e minhas, com ficha e botão assumir; ações de coordenador não aparecem
