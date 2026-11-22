# Regras de prospecção são configuração da organização, e a base de CNPJ segue o catálogo

Quem define as regras de prospecção é a organização, não nós. Elas ficam editáveis na plataforma em dois níveis: por campanha (municípios, segmentos, tiers-alvo, limite de empresas, teto de gasto) e por organização (catálogo de segmentos, perfil ideal, pesos e cortes da nota, exclusões). Os pesos e cortes começam com os valores do Plano v2 (40/25/20/15; A ≥ 80, B ≥ 60, C ≥ 40).

Como o coordenador pode escolher qualquer município, a base de CNPJ não é carregada por campanha: carregamos o recorte do estado inteiro, só com empresas ativas e com os CNAEs do catálogo da organização. Uma nova carga só é necessária quando o catálogo ganha um segmento.

**Consequences**

- Na v0 a carga é um script rodado fora da plataforma, porque o Render grátis não tem memória para os arquivos da Receita; no VPS ela vira uma tarefa disparada pela tela do catálogo.
- O recorte precisa caber no Supabase grátis (cerca de 500 MB). Medir na primeira carga; se não couber, limitar à região da organização.
- Mudar pesos ou cortes muda o tier de empresas futuras, não das já triadas; cada nota guarda a versão das regras usada.
