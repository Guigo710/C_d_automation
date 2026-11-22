# Commercial Department Automation

Plataforma por assinatura em que agentes de IA encontram e pontuam empresas com perfil de comprador de uma organização, um coordenador decide quais seguem e os vendedores as assumem para abordar. A Destak é a primeira organização.

## Plataforma

**Organização**:
Uma empresa que assina a plataforma e usa seus serviços; seus dados, configurações e chaves de API são só dela. A Destak é a primeira.
_Avoid_: cliente, tenant, conta, empresa

**Empresa**:
Um estabelecimento comercial encontrado pelos agentes como possível comprador de uma organização.
_Avoid_: cliente, lead, prospect

**Teto de gasto**:
O valor máximo que uma organização ou campanha pode gastar com dados e IA; ao atingi-lo, os agentes param.
_Avoid_: limite, orçamento, budget

## Pessoas

**Coordenador**:
Pessoa da área comercial de uma organização que configura campanhas e decide, na triagem, quais empresas seguem para os vendedores.
_Avoid_: gestor, aprovador, admin

**Vendedor**:
Pessoa da equipe comercial que assume empresas aprovadas e faz o contato com elas.
_Avoid_: representante, SDR, usuário

## Prospecção

**Campanha**:
Um esforço de prospecção com região, segmentos e tiers-alvo definidos, dentro do qual as empresas são encontradas, triadas e assumidas.
_Avoid_: projeto, busca, lista

**Catálogo de segmentos**:
O conjunto de segmentos de mercado que uma organização prospecta; as campanhas só podem escolher segmentos do catálogo.
_Avoid_: lista de CNAEs, nichos

**Perfil ideal**:
A descrição, escrita pela organização, do que torna uma empresa muito boa, boa ou aceitável como compradora; é a base da nota de aderência.
_Avoid_: ICP, persona, cliente ideal

**Agente de prospecção**:
O componente que, dada uma campanha, encontra empresas e devolve candidatos com evidências; de onde ele tira os dados é escolha de quem o escreve.
_Avoid_: Agente 1, robô, crawler

**Candidato**:
Uma empresa devolvida pelo agente de prospecção que ainda não passou pela triagem.
_Avoid_: lead, prospect, resultado

**Evidência**:
O registro de onde veio um dado de uma empresa: a fonte, o link e a data em que foi coletado.
_Avoid_: fonte, referência, log

**Triagem**:
A etapa em que o coordenador aprova ou recusa cada empresa encontrada pelos agentes, sempre com motivo na recusa.
_Avoid_: filtragem, qualificação, validação

**Tier**:
A classe de prioridade de uma empresa na campanha: A (muito boa), B (boa) ou C (aceitável).
_Avoid_: nível, categoria, rating

**Ficha de abordagem**:
Resumo de uma empresa aprovada, escrito para o vendedor ler antes do primeiro contato, com os fatos que sustentam a abordagem.
_Avoid_: brief, resumo, perfil

**Assumir**:
O ato de um vendedor tornar-se o único responsável por uma empresa aprovada; o primeiro que assume fica com ela.
_Avoid_: pegar, reservar, atribuir (atribuir é quando o coordenador escolhe o vendedor)
