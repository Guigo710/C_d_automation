# Spec: v0 de demonstração da Commercial Department Automation

Status: ready-for-agent

## Problem Statement

A Destak, primeira organização da plataforma, ainda não decidiu contratar. Hoje a prospecção de novas empresas compradoras é manual e desorganizada, e o levantamento de requisitos enviado a ela ainda não tem respostas. Para fechar a assinatura, precisamos mostrar, com custo de infraestrutura zero, que agentes de IA encontram empresas reais da região dela, dão uma nota útil a cada uma, e que o coordenador e os vendedores conseguem trabalhar essas empresas de forma organizada, sem um vendedor abordar a empresa de outro.

## Solution

Uma primeira versão (v0) da plataforma, já preparada para várias organizações, em que:

- o coordenador cria uma campanha (municípios, segmentos do catálogo, tiers-alvo, limite de empresas e teto de gasto) e manda executá-la;
- o agente de prospecção encontra candidatos com evidências; o agente de qualificação aplica exclusões, dá notas e sugere o tier;
- o coordenador faz a triagem num kanban, aprova ou recusa (recusa sempre com motivo) e exporta os aprovados;
- as empresas aprovadas ganham uma ficha de abordagem escrita pela IA e ficam disponíveis aos vendedores da campanha;
- o vendedor assume uma empresa (o primeiro a assumir fica com ela) e só então vê os dados de contato; o coordenador também pode atribuir e transferir.

A v0 usa dados reais numa campanha pequena e não faz nenhum contato com as empresas. Ela é entregue em três marcos: M1 (dados reais na tela), M2 (triagem e ficha; prévia para a Destak) e M3 (login com papéis, assumir, atribuir, transferir; v0 completa).

## User Stories

### Organização e acesso

1. Como administrador da plataforma, quero criar uma organização e seus primeiros usuários sem tela de cadastro, para que a Destak comece a usar sem esperarmos um fluxo de cadastro aberto.
2. Como usuário de uma organização, quero entrar com e-mail e senha, para acessar só o que meu papel permite.
3. Como usuário, quero recuperar minha senha por e-mail, para não depender do administrador quando a esqueço.
4. Como membro de uma organização, quero nunca ver dados de outra organização, mesmo que eu tente acessar o endereço de um recurso dela, para que os dados de cada organização fiquem isolados.
5. Como vendedor, quero que as ações de coordenador nem apareçam na minha tela, para não me confundir com o que não posso fazer.
6. Como coordenador, quero que a plataforma recuse uma ação proibida ao meu papel mesmo que alguém a chame direto pela API, para que a segurança não dependa da tela.

### Configuração da organização

7. Como administrador da organização, quero cadastrar as chaves de API dos fornecedores (IA e fontes de dados) dentro da plataforma, para que a organização pague direto os próprios fornecedores.
8. Como administrador da organização, quero que as chaves fiquem guardadas cifradas e nunca sejam mostradas inteiras depois de salvas, para que não vazem pela tela.
9. Como administrador da organização, quero definir um teto de gasto mensal para dados e IA, para não ter surpresa na fatura.
10. Como administrador da organização, quero ver quanto já foi gasto no mês, para saber quanto falta até o teto.
11. Como organização, quero que meu catálogo de segmentos, meu perfil ideal, os pesos e cortes da nota, meus municípios com rota de entrega, minha lista de empresas que já são clientes e minha lista de bloqueio sejam configuração minha, e não código, para que a plataforma sirva a mim e a outras organizações.

### Campanha

12. Como coordenador, quero criar uma campanha escolhendo municípios, segmentos do catálogo, tiers-alvo, limite de empresas e teto de gasto, para direcionar a prospecção.
13. Como coordenador, quero escolher apenas segmentos do catálogo da minha organização, para que a campanha não peça dados que o agente não sabe buscar.
14. Como coordenador, quero definir quais vendedores participam da campanha, para que só eles vejam e assumam as empresas dela.
15. Como coordenador, quero listar as campanhas da organização com status (rascunho, ativa, pausada, encerrada), para acompanhar o que está em andamento.
16. Como coordenador, quero mandar executar a prospecção de uma campanha e voltar ao trabalho sem esperar, para que a tela não fique travada enquanto os agentes trabalham.
17. Como coordenador, quero ver o andamento da execução (empresas encontradas, qualificadas, gasto até agora, status), para saber quando a triagem está pronta.
18. Como coordenador, quero que a execução pare sozinha ao atingir o limite de empresas ou o teto de gasto e termine como parcial, para nunca estourar o valor definido.
19. Como coordenador, quero que uma execução interrompida (por exemplo, quando o servidor dorme) continue de onde parou no próximo acesso, sem duplicar empresas nem cobrar de novo o que já foi feito.

### Prospecção e qualificação

20. Como coordenador, quero que cada candidato traga as evidências de cada dado (fonte, link e data), para confiar no que estou vendo.
21. Como coordenador, quero que empresas inativas, fora da região, que já são clientes, duplicadas ou na lista de bloqueio já venham recusadas com o motivo sugerido, para não perder tempo com elas.
22. Como coordenador, quero poder restaurar um candidato recusado por regra, para corrigir uma sugestão errada.
23. Como coordenador, quero que cada candidato tenha notas de aderência, potencial, geografia e qualidade dos dados, uma nota total e um tier sugerido, para priorizar a triagem.
24. Como coordenador, quero ler a justificativa da IA para as notas de aderência e potencial, com as evidências citadas, para entender por que ela sugeriu aquele tier.
25. Como coordenador, quero ver o que falta saber sobre cada candidato (lacunas), para decidir se vale aprovar mesmo assim.
26. Como coordenador, quero que candidatos em que a IA teve pouca confiança apareçam com o selo "baixa confiança", para olhá-los com mais cuidado.
27. Como coordenador, quero que candidatos com nota total abaixo do corte de C venham sugeridos como recusados por estarem fora do perfil, para focar nos que importam.
28. Como organização, quero que a nota de cada candidato guarde a versão das regras usada, para que mudar pesos ou cortes não altere tiers já decididos.

### Triagem

29. Como coordenador, quero ver os candidatos da campanha num kanban (pendentes, aprovados, recusados), para triar com rapidez.
30. Como coordenador, quero abrir um candidato numa gaveta lateral com todos os dados, notas, evidências e lacunas, para decidir sem sair do kanban.
31. Como coordenador, quero aprovar vários candidatos de uma vez, para triar em lote.
32. Como coordenador, quero que toda recusa exija um motivo da lista (fora do perfil, CNPJ inativo, fora da região, dados incompletos, já é cliente, duplicado, opt-out), para que a recusa sirva de aprendizado.
33. Como coordenador, quero poder mudar o tier sugerido, com justificativa, para que minha decisão prevaleça sobre a da IA.
34. Como coordenador, quero filtrar e ordenar os candidatos por tier, nota e segmento, para triar primeiro os melhores.
35. Como coordenador, quero enviar os aprovados para os vendedores com um clique ("subir para operação"), e que um clique duplo ou repetido não crie empresas duplicadas, para não bagunçar a carteira.
36. Como coordenador, quero exportar os aprovados de uma campanha para Excel, para levar a lista a uma reunião.
37. Como vendedor, quero não conseguir exportar listas, para que a carteira da empresa não saia junto com quem sai da empresa.

### Ficha de abordagem

38. Como vendedor, quero ler uma ficha de abordagem de cada empresa aprovada, com os fatos que sustentam o contato, para abordar com contexto.
39. Como vendedor, quero ver "ficha em preparo" enquanto a ficha não fica pronta, para saber que ela está a caminho.
40. Como coordenador, quero que a ficha cite só fatos com evidência, para que o vendedor não repita algo inventado pela IA.

### Operação: assumir, atribuir, transferir

41. Como vendedor, quero ver as empresas aprovadas das campanhas de que participo, com nome, segmento, município, tier e ficha, para escolher quais assumir.
42. Como vendedor, quero não ver telefone, e-mail nem nome do contato de uma empresa que ainda não assumi, para não abordar por fora a empresa de outro.
43. Como vendedor, quero assumir uma empresa e passar a ver os dados de contato dela, para começar a abordagem.
44. Como vendedor, quero que, se outro vendedor assumir a mesma empresa ao mesmo tempo, só um de nós fique com ela e o outro receba um aviso claro, para não haver disputa.
45. Como vendedor, quero ver a lista das minhas empresas separada das disponíveis, para focar na minha carteira.
46. Como coordenador, quero atribuir uma empresa aprovada direto a um vendedor da campanha, para distribuir sem esperar alguém assumir.
47. Como coordenador, quero transferir uma empresa de um vendedor para outro, para corrigir distribuições ou cobrir ausências.
48. Como coordenador, quero ver sempre todos os dados de contato de todas as empresas da campanha, para acompanhar a operação.
49. Como coordenador, quero ver o histórico de cada empresa (aprovação, promoção, quem assumiu, atribuições e transferências, com quem e quando), para entender o que aconteceu com ela.
50. Como vendedor, quero receber erro "não encontrada" ao tentar abrir uma empresa de outro vendedor pelo endereço, para que a plataforma nem revele que ela existe.

### Auditoria e custos

51. Como administrador da organização, quero que login, exportação, aprovação, promoção e troca de responsável fiquem registrados num registro que não pode ser alterado nem apagado, para ter rastro de tudo.
52. Como administrador da organização, quero ver o custo de cada execução de campanha, para entender quanto custa cada empresa aprovada.
53. Como organização, quero que uma resposta da IA já paga não seja paga de novo quando a mesma pergunta se repetir, para economizar.

### Agente de prospecção

54. Como autor do agente de prospecção, quero receber a campanha (organização, municípios, segmentos e CNAEs, limite de empresas e saldo do teto) e devolver candidatos com evidências e custo, sem me preocupar com banco, fila, deduplicação, exclusões ou permissões, para mexer só na lógica de prospecção.
55. Como autor do agente de prospecção, quero escolher livremente as fontes de dados (base de CNPJ, Google, sites ou outras), para evoluir a prospecção sem mudar a plataforma.
56. Como desenvolvedor da plataforma, quero um agente de prospecção falso que devolve candidatos de exemplo no mesmo formato, para construir e testar o resto antes de o agente real ficar pronto.
57. Como autor do agente de prospecção, quero trocar o agente falso pelo real por configuração, sem mexer no restante do código.

## Implementation Decisions

### Arquitetura e implantação

- Cliente-servidor: SPA em React com Vite e TypeScript conversa com uma única API FastAPI (Python 3.12), organizada como monólito modular em camadas (rotas, serviço, repositório, adaptadores). Rotas não acessam o banco; regras de negócio ficam nos serviços; todo SQL fica nos repositórios; cada fornecedor externo fica atrás de uma interface própria.
- Banco PostgreSQL gerenciado no Supabase, região São Paulo, com Row Level Security por organização (ADR 0002). Login pelo Supabase Auth com e-mail e senha (ADR 0003); a API só valida o token do Supabase.
- O token do usuário carrega `organizacao_id` e o papel, preenchidos a partir da tabela de perfis da plataforma (não pelo próprio usuário). As políticas de RLS e as checagens da API usam essas duas informações.
- v0 em planos gratuitos: frontend na Vercel; API no Render, com o worker de jobs no mesmo processo; fila de jobs numa tabela do PostgreSQL (ADR 0004). Sem Redis nem Celery. A aplicação é empacotada como imagem Docker desde já.
- Tipos do frontend gerados a partir do OpenAPI da API, para que uma mudança de contrato quebre o build, não a tela.
- Toda tabela de dados de negócio tem `organizacao_id` desde o primeiro dia; nada específico da Destak fica no código (ADR 0001).

### Módulos

- **Organizações e perfis**: organização, perfis de usuário (vínculo do usuário do Supabase Auth com organização, papel e status ativo), configuração da organização e chaves de API cifradas pela aplicação. Papéis: administrador, coordenador, vendedor.
- **Permissões**: mapa único de permissão para papéis, aplicado em cada rota; toda consulta de vendedor recebe o filtro de escopo no SQL (campanhas de que é membro e empresas de que é responsável); o serializador mascara nome, telefone e e-mail do contato quando quem pede não é coordenador nem responsável.
- **Configuração da organização**: catálogo de segmentos (segmento e CNAEs), perfil ideal em texto, pesos e cortes da nota (padrão 40/25/20/15; A ≥ 80, B ≥ 60, C ≥ 40), municípios com rota de entrega e municípios atendidos sem rota, empresas que já são clientes (por CNPJ), lista de bloqueio (CNPJ, e-mail, telefone, domínio), teto de gasto mensal. Na v0 só as chaves de API e o teto mensal têm tela; o restante é preenchido pelo administrador da plataforma (ADR 0005). Cada alteração de regras gera uma nova versão.
- **Campanhas**: criação e edição, membros (vendedores), status, teto de gasto e limite de empresas.
- **Execuções (jobs)**: fila em tabela com estados na fila, executando, concluída, parcial, falhou; contagens, custo, erro e última atividade. O worker retoma jobs não terminados ao iniciar e periodicamente. Toda tarefa é idempotente. A fila fica atrás de uma interface própria, para ser trocada por Celery no VPS.
- **Prospecção**: orquestra a chamada ao agente de prospecção, grava empresas, evidências e candidatos com status "coletado", deduplica por CNPJ dentro da campanha e entre campanhas ativas, e para ao atingir o limite de empresas ou o saldo do teto.
- **Qualificação (Agente 2)**: lê candidatos coletados em lotes, aplica exclusões por regra (CNPJ inativo, fora da região, já é cliente, duplicado, opt-out; esses vão para recusados com a etiqueta "sugerido"), valida contatos (sintaxe e domínio de e-mail; telefone com DDD válido), calcula geografia (100 com rota, 60 atendido sem rota, 0 fora) e qualidade dos dados (30 CNPJ ativo casado com loja, 30 canal comercial válido, 20 site oficial, 20 três ou mais evidências com menos de 180 dias) por regra, pede à IA as notas de aderência e potencial com justificativa e evidências citadas, calcula o total e o tier por código e grava o candidato como "pendente" com notas, tier sugerido, motivos, lacunas, modelo, versão do prompt e versão das regras. Confiança abaixo de 0,6 marca "baixa confiança" (sem segunda análise com outro modelo na v0). Total abaixo do corte de C sugere recusa por fora do perfil.
- **Triagem**: kanban de candidatos pendentes, aprovados e recusados; aprovação em lote; recusa com motivo obrigatório; troca de tier com justificativa; restauração de recusa sugerida.
- **Operação (Agente 3)**: promoção dos aprovados numa única transação com chave de idempotência por clique (ignora clientes atuais e bloqueados; repetir o lote não duplica); empresas promovidas entram sem responsável; assumir com regra "primeiro a assumir vence" garantida pelo banco; atribuir e transferir pelo coordenador; histórico de cada empresa. Após a promoção, um job gera a ficha de abordagem de cada empresa pela IA.
- **IA**: interface única de cliente de modelo, com implementação para a Claude API usando Claude Haiku 5.5, saída estruturada validada antes de gravar (resposta fora do esquema ou que cite evidência inexistente é descartada e reenviada uma vez; na segunda falha o caso vai para revisão), cache de respostas por hash (modelo, versão do prompt, entrada), checagem do teto antes de cada chamada, no máximo 2 novas tentativas e timeout de 60 segundos. Usa a chave de API da organização.
- **Exportação**: XLSX dos aprovados de uma campanha, só para coordenador, gerado sob demanda e registrado na auditoria.
- **Auditoria**: registro só de inserção (o banco recusa alteração e exclusão) para login, exportação, aprovação, promoção e troca de responsável.

### Contrato do agente de prospecção

- O agente é um componente Python com um ponto de entrada que recebe uma fotografia da campanha (organização, municípios por código IBGE, segmentos e CNAEs, limite de empresas e saldo do teto) e devolve candidatos de forma incremental.
- Cada candidato traz: CNPJ, razão social, nome fantasia, endereço, município, segmento, contatos e site (cada um com a fonte), sinais comerciais (por exemplo número de lojas, linhas de produto, canal de compras), evidências de cada campo (fonte, link e data) e o custo incremental gasto para obtê-lo.
- A plataforma é dona de: gravar, deduplicar, aplicar exclusões, controlar o teto (deixa de consumir candidatos quando o saldo acaba), registrar o andamento do job e retomar após interrupção. Como a plataforma deduplica por CNPJ, chamar o agente de novo depois de uma interrupção é seguro.
- As fontes de dados, incluindo a eventual carga da base de CNPJ da Receita, são responsabilidade de quem escreve o agente.
- O agente usado é escolhido por configuração. A v0 inclui um agente falso que devolve candidatos de um arquivo de exemplo no formato acima.

### Estados

- Candidato: coletado → pendente → aprovado ou recusado (recusado pode ser "sugerido" por regra e restaurado pelo coordenador). Aprovado → promovido.
- Empresa da campanha (promovida): sem responsável → com responsável (por assumir ou atribuir); o responsável pode mudar por transferência.
- Campanha: rascunho, ativa, pausada, encerrada.

### Esquema

- Partir do modelo de 17 tabelas do Plano v2, com estas mudanças: `organizacao_id` em todas as tabelas de negócio; a tabela de usuários com senha e MFA dá lugar a perfis ligados ao Supabase Auth; novas tabelas de configuração da organização (versionada), catálogo de segmentos, municípios com rota e chaves de API cifradas; a fila de jobs vira tabela. Mensagens automáticas e eventos de provedores (Agente 4) ficam de fora.
- CNPJ aceita o formato alfanumérico (IN RFB 2.229/2024).

### API

- Rotas por recurso: campanhas, execuções, candidatos (triagem), promoções, empresas da campanha (listar, assumir, atribuir, transferir), exportações, configuração da organização (chaves e teto), auditoria.
- Iniciar uma execução devolve o identificador do job imediatamente; a tela acompanha o progresso por consulta periódica.
- A promoção exige o cabeçalho de chave de idempotência.
- Recurso fora do escopo do usuário responde "não encontrado", sem revelar que existe.
- Listagens paginadas no servidor.

### Telas da v0

- Login e recuperação de senha.
- Campanhas: lista, criação e edição (municípios, segmentos do catálogo, tiers-alvo, limite, teto, vendedores).
- Execução: andamento e custo.
- Triagem: kanban com gaveta lateral do candidato, aprovação em lote, recusa com motivo, troca de tier.
- Empresas da campanha: para o vendedor, disponíveis e minhas, com ficha e botão assumir; para o coordenador, todas, com atribuir e transferir e o histórico.
- Configuração da organização: chaves de API e teto mensal, com o gasto do mês.

## Testing Decisions

- Um bom teste exercita o comportamento externo pela API, como um cliente faria, e verifica o resultado observável (resposta, estado lido de volta pela API), nunca detalhes internos como nomes de funções ou consultas.
- **Ponto de teste principal: a API HTTP** rodando contra um PostgreSQL real com o esquema, as políticas de RLS e as funções do banco aplicados, chamada com tokens de teste assinados com um segredo de teste, para usuários de papéis diferentes em **duas organizações** distintas.
- **Dois encaixes substituídos por versões falsas nos testes**: o agente de prospecção (o agente falso da própria v0) e o cliente de IA (respostas determinísticas, sem rede e sem custo). A fila é drenada de forma síncrona nos testes.
- Comportamentos que precisam de teste:
  - isolamento entre organizações, inclusive quando o código da rota não filtra (o RLS precisa barrar);
  - mascaramento de contato para vendedor não responsável e visibilidade total para o coordenador;
  - "primeiro a assumir vence" com duas tentativas concorrentes;
  - promoção idempotente (repetir o lote ou o clique não duplica) e que ignora clientes atuais e bloqueados;
  - recusa sem motivo é rejeitada; troca de tier sem justificativa é rejeitada;
  - exclusões por regra geram as recusas sugeridas certas;
  - cálculo do total e do tier a partir das notas e dos pesos e cortes da organização, e que a versão das regras fica gravada;
  - a execução para no limite de empresas e no saldo do teto e termina como parcial;
  - uma execução interrompida retoma sem duplicar empresas nem repetir custo;
  - vendedor não exporta, não atribui, não transfere e não promove;
  - atribuir e transferir registram histórico; o registro de auditoria recusa alteração e exclusão;
  - chave de API nunca volta inteira pela API depois de salva.
- O frontend fica só com checagem de tipos na v0.
- Não há testes anteriores neste repositório. Como referência, o Plano v2 validou o esquema com 21 testes de comportamento em PostgreSQL 16 (promoção repetida, disputa por assumir, auditoria imutável, CNPJ alfanumérico); esses cenários devem ser reaproveitados no nível da API.

## Out of Scope

- Agente 4: envio automático de e-mail ou WhatsApp e qualquer contato com as empresas.
- Registro de contatos, follow-up, funil de vendas, motivos de perda, relatórios e indicadores.
- Devolução automática de empresa sem contato e distribuição automática por região.
- Segunda análise com Claude Sonnet 5.5 em casos de baixa confiança; Brave Search como fonte.
- Telas de catálogo de segmentos, perfil ideal, pesos e cortes, municípios com rota, clientes atuais e lista de bloqueio (preenchidos pelo administrador da plataforma na v0).
- Tela de usuários e convites (contas criadas pelo administrador da plataforma na v0).
- Login com Google ou Microsoft e MFA.
- Cadastro aberto de organizações, planos, cobrança automática da assinatura.
- Identidade visual por organização.
- A lógica do agente de prospecção real e a carga da base de CNPJ (responsabilidade do autor do agente).
- VPS, Redis, Celery, ambiente de staging e alta disponibilidade.
- Notificações aos vendedores.
- Integrações com CRM, ERP ou ferramentas de relatório.

## Further Notes

- Marcos: **M1** — esqueleto da plataforma, configuração da organização semeada, campanha, execução com o agente falso e lista de candidatos; **M2** — qualificação, kanban de triagem, promoção e ficha de abordagem (prévia informal para a Destak, que serve também para colher as respostas 3.6, 2.4 e 3.4 do levantamento); **M3** — login com papéis, telas por papel, assumir, atribuir, transferir, contato oculto e exportação (v0 completa).
- O serviço gratuito do Render dorme após cerca de 15 minutos sem acesso e leva perto de 1 minuto para acordar: abrir o sistema antes de uma demonstração.
- A Claude API exige créditos pagos (a demo consome poucos dólares) e o Google Places exige conta de faturamento com cartão mesmo dentro da cota gratuita.
- Custos de referência do Plano v2: cerca de US$ 25 em fontes de dados e US$ 2 a 3 de IA por 1.000 empresas.
- Vocabulário: ver `GLOSSARY.md`. Decisões: ver `docs/adr/0001` a `0005`.
