-- Registro de auditoria: o banco só aceita inclusões (ticket 02).

CREATE TABLE auditoria (
  id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  organizacao_id uuid NOT NULL DEFAULT app.organizacao_atual() REFERENCES organizacoes(id),
  usuario_id     uuid,
  acao           text NOT NULL,
  recurso_tipo   text,
  recurso_id     text,
  detalhes       jsonb NOT NULL DEFAULT '{}'::jsonb,
  criado_em      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX auditoria_organizacao_criado_idx ON auditoria (organizacao_id, criado_em DESC);

-- Nem o dono da tabela altera ou apaga um evento.
CREATE OR REPLACE FUNCTION app.auditoria_imutavel() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'auditoria só aceita inclusões'
    USING ERRCODE = 'insufficient_privilege';
END;
$$;

CREATE TRIGGER auditoria_sem_alteracao
  BEFORE UPDATE OR DELETE ON auditoria
  FOR EACH ROW EXECUTE FUNCTION app.auditoria_imutavel();

ALTER TABLE auditoria ENABLE ROW LEVEL SECURITY;

CREATE POLICY auditoria_inclusao ON auditoria
  FOR INSERT TO authenticated
  WITH CHECK (organizacao_id = app.organizacao_atual());

CREATE POLICY auditoria_leitura_administrador ON auditoria
  FOR SELECT TO authenticated
  USING (organizacao_id = app.organizacao_atual() AND app.papel_atual() = 'administrador');

GRANT INSERT, SELECT ON auditoria TO authenticated;
