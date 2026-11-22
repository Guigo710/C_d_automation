# 06: Limite, teto de gasto e retomada da execução

**What to build:** a execução de uma campanha nunca passa do limite de empresas nem do teto de gasto (da campanha e mensal da organização): ao atingir qualquer um, para e termina como parcial. Se o serviço dormir ou cair no meio, a execução continua de onde parou no próximo acesso, sem duplicar empresas nem repetir custo.

**Blocked by:** 04 (Execução da prospecção com o agente falso), 05 (Chaves de API e teto mensal)

**Status:** ready-for-agent

- [ ] O agente recebe o saldo do teto (o menor entre o saldo da campanha e o saldo mensal da organização)
- [ ] A plataforma deixa de consumir candidatos quando o limite de empresas ou o saldo acaba, e o job termina como parcial
- [ ] Custo de cada execução registrado e somado ao gasto do mês
- [ ] O worker retoma, ao iniciar e periodicamente, jobs não terminados cuja última atividade ficou parada
- [ ] Teste: interromper uma execução no meio e retomar não duplica candidatos nem soma custo duas vezes
- [ ] Teste: execução para exatamente no limite e no teto
