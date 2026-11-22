-- Chaves de API por organização (cifradas pela aplicação) e teto de gasto mensal (ticket 05).

ALTER TABLE organizacoes
  ADD COLUMN teto_mensal_usd numeric(10, 2) NOT NULL DEFAULT 50 CHECK (teto_mensal_usd >= 0);

CREATE POLICY atualizacao_administrador ON organizacoes
  FOR UPDATE TO authenticated
  USING (id = app.organizacao_atual() AND app.papel_atual() = 'administrador')
  WITH CHECK (id = app.organizacao_atual() AND app.papel_atual() = 'administrador');
GRANT UPDATE (teto_mensal_usd) ON organizacoes TO authenticated;

CREATE TABLE chaves_api (
  organizacao_id uuid NOT NULL DEFAULT app.organizacao_atual() REFERENCES organizacoes(id),
  fornecedor     text NOT NULL CHECK (fornecedor IN ('anthropic', 'google_places', 'brave')),
  chave_cifrada  bytea NOT NULL,
  final          text NOT NULL,
  atualizada_por uuid DEFAULT app.usuario_atual(),
  atualizada_em  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organizacao_id, fornecedor)
);

ALTER TABLE chaves_api ENABLE ROW LEVEL SECURITY;

-- O administrador gerencia; os agentes (papel 'sistema') só leem para usar.
CREATE POLICY administrador ON chaves_api FOR ALL TO authenticated
  USING (organizacao_id = app.organizacao_atual() AND app.papel_atual() = 'administrador')
  WITH CHECK (organizacao_id = app.organizacao_atual() AND app.papel_atual() = 'administrador');
CREATE POLICY leitura_sistema ON chaves_api FOR SELECT TO authenticated
  USING (organizacao_id = app.organizacao_atual() AND app.papel_atual() = 'sistema');

GRANT SELECT, INSERT, UPDATE, DELETE ON chaves_api TO authenticated;

-- Gasto do mês corrente (horário de Brasília) com dados e IA, somando o custo dos jobs.
CREATE OR REPLACE FUNCTION app.gasto_do_mes() RETURNS numeric
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT coalesce(sum(custo_usd), 0)
    FROM jobs
   WHERE organizacao_id = app.organizacao_atual()
     AND date_trunc('month', criado_em AT TIME ZONE 'America/Sao_Paulo')
       = date_trunc('month', now() AT TIME ZONE 'America/Sao_Paulo')
$$;
GRANT EXECUTE ON FUNCTION app.gasto_do_mes() TO authenticated;
