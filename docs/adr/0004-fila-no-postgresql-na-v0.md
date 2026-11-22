# Fila no PostgreSQL e Render grátis na v0, Celery e Redis depois

O Plano v2 prevê workers Celery com Redis num VPS. Como a v0 é uma demonstração grátis com campanhas de algumas centenas de empresas, ela roda no plano gratuito do Render, com o worker no mesmo processo da API, lendo uma tabela de fila no próprio PostgreSQL (ADR 0002). Não usamos Redis nem Celery até a Destak assinar e o sistema ir para VPS. A fila fica atrás de uma interface própria, para que trocá-la por Celery não mexa nas regras de negócio.

**Consequences**

- O serviço grátis do Render dorme após cerca de 15 minutos sem acesso e leva perto de 1 minuto para acordar; o sistema deve ser aberto antes de uma demonstração.
- Se o serviço dormir no meio de uma campanha, o trabalho continua no próximo acesso: toda tarefa precisa ser idempotente e o estado do job vive no banco, nunca na memória.
- A aplicação é empacotada como imagem Docker desde a v0, para que mudar para o VPS seja só publicar a mesma imagem em outro lugar.
- Plano B, caso o Render não sirva: máquina virtual Oracle Cloud Always Free em São Paulo.
