-- Execução da prospecção: fila de jobs, empresas, evidências, contatos e candidatos
-- (ticket 04, ADR 0004).

-- Os workers agem em nome de uma organização com o papel 'sistema'.
CREATE OR REPLACE FUNCTION app.pode_ver_campanha(campanha uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT app.papel_atual() IN ('administrador', 'coordenador', 'sistema')
      OR EXISTS (
           SELECT 1 FROM campanha_membros m
            WHERE m.campanha_id = campanha AND m.usuario_id = app.usuario_atual()
         )
$$;

-- Fila de jobs no PostgreSQL. O worker reivindica com FOR UPDATE SKIP LOCKED e renova
-- `lease_ate`; um job "executando" com lease vencido volta a ser reivindicável.
CREATE TABLE jobs (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organizacao_id   uuid NOT NULL DEFAULT app.organizacao_atual() REFERENCES organizacoes(id),
  tipo             text NOT NULL,
  campanha_id      uuid REFERENCES campanhas(id),
  status           text NOT NULL DEFAULT 'na_fila'
                   CHECK (status IN ('na_fila', 'executando', 'concluida', 'parcial', 'falhou')),
  motivo_parada    text,
  encontradas      integer NOT NULL DEFAULT 0,
  gravadas         integer NOT NULL DEFAULT 0,
  duplicadas       integer NOT NULL DEFAULT 0,
  custo_usd        numeric(12, 4) NOT NULL DEFAULT 0,
  erro             text,
  tentativas       integer NOT NULL DEFAULT 0,
  criado_por       uuid DEFAULT app.usuario_atual(),
  criado_em        timestamptz NOT NULL DEFAULT now(),
  iniciado_em      timestamptz,
  terminado_em     timestamptz,
  ultima_atividade timestamptz,
  lease_ate        timestamptz
);
CREATE INDEX jobs_pendentes_idx ON jobs (criado_em) WHERE status IN ('na_fila', 'executando');
CREATE INDEX jobs_campanha_idx ON jobs (campanha_id, criado_em DESC);

-- Um estabelecimento por CNPJ, por organização, com dados públicos.
CREATE TABLE empresas (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organizacao_id      uuid NOT NULL DEFAULT app.organizacao_atual() REFERENCES organizacoes(id),
  cnpj                char(14) NOT NULL CHECK (cnpj ~ '^[0-9A-Z]{12}[0-9]{2}$'),
  razao_social        text NOT NULL,
  nome_fantasia       text,
  situacao_cadastral  text,
  endereco            text,
  municipio_ibge      char(7),
  segmento            text,
  site                text,
  sinais              jsonb NOT NULL DEFAULT '{}'::jsonb,
  atualizada_em       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organizacao_id, cnpj)
);

CREATE TABLE contatos (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organizacao_id uuid NOT NULL DEFAULT app.organizacao_atual() REFERENCES organizacoes(id),
  empresa_id     uuid NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
  tipo           text NOT NULL CHECK (tipo IN ('telefone', 'email', 'whatsapp')),
  valor          text NOT NULL,
  nome           text,
  fonte          text NOT NULL,
  coletado_em    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (empresa_id, tipo, valor)
);

CREATE TABLE evidencias (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organizacao_id uuid NOT NULL DEFAULT app.organizacao_atual() REFERENCES organizacoes(id),
  empresa_id     uuid NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
  campo          text NOT NULL,
  valor          text,
  fonte          text NOT NULL,
  url            text,
  coletado_em    timestamptz NOT NULL
);
CREATE INDEX evidencias_empresa_idx ON evidencias (empresa_id);

CREATE TABLE candidatos (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organizacao_id uuid NOT NULL DEFAULT app.organizacao_atual() REFERENCES organizacoes(id),
  campanha_id    uuid NOT NULL REFERENCES campanhas(id),
  empresa_id     uuid NOT NULL REFERENCES empresas(id),
  job_id         uuid REFERENCES jobs(id),
  status         text NOT NULL DEFAULT 'coletado'
                 CHECK (status IN ('coletado', 'pendente', 'aprovado', 'recusado')),
  criado_em      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (campanha_id, empresa_id)
);
CREATE INDEX candidatos_campanha_status_idx ON candidatos (campanha_id, status);
CREATE INDEX candidatos_empresa_idx ON candidatos (empresa_id);

ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE empresas ENABLE ROW LEVEL SECURITY;
ALTER TABLE contatos ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidencias ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidatos ENABLE ROW LEVEL SECURITY;

-- Jobs: coordenador cria; coordenador, administrador e sistema leem; sistema atualiza.
CREATE POLICY leitura ON jobs FOR SELECT TO authenticated
  USING (organizacao_id = app.organizacao_atual()
         AND app.papel_atual() IN ('administrador', 'coordenador', 'sistema'));
CREATE POLICY criacao ON jobs FOR INSERT TO authenticated
  WITH CHECK (organizacao_id = app.organizacao_atual()
              AND app.papel_atual() IN ('coordenador', 'sistema'));
CREATE POLICY atualizacao_sistema ON jobs FOR UPDATE TO authenticated
  USING (organizacao_id = app.organizacao_atual() AND app.papel_atual() = 'sistema');

-- Dados de empresas: a organização lê; só o sistema (os agentes) escreve.
CREATE POLICY leitura ON empresas FOR SELECT TO authenticated
  USING (organizacao_id = app.organizacao_atual());
CREATE POLICY escrita_sistema ON empresas FOR ALL TO authenticated
  USING (organizacao_id = app.organizacao_atual() AND app.papel_atual() = 'sistema')
  WITH CHECK (organizacao_id = app.organizacao_atual() AND app.papel_atual() = 'sistema');

CREATE POLICY leitura ON contatos FOR SELECT TO authenticated
  USING (organizacao_id = app.organizacao_atual());
CREATE POLICY escrita_sistema ON contatos FOR ALL TO authenticated
  USING (organizacao_id = app.organizacao_atual() AND app.papel_atual() = 'sistema')
  WITH CHECK (organizacao_id = app.organizacao_atual() AND app.papel_atual() = 'sistema');

CREATE POLICY leitura ON evidencias FOR SELECT TO authenticated
  USING (organizacao_id = app.organizacao_atual());
CREATE POLICY escrita_sistema ON evidencias FOR ALL TO authenticated
  USING (organizacao_id = app.organizacao_atual() AND app.papel_atual() = 'sistema')
  WITH CHECK (organizacao_id = app.organizacao_atual() AND app.papel_atual() = 'sistema');

-- Candidatos: triagem é do coordenador; o sistema grava e qualifica.
CREATE POLICY leitura ON candidatos FOR SELECT TO authenticated
  USING (organizacao_id = app.organizacao_atual()
         AND app.papel_atual() IN ('administrador', 'coordenador', 'sistema'));
CREATE POLICY escrita ON candidatos FOR ALL TO authenticated
  USING (organizacao_id = app.organizacao_atual()
         AND app.papel_atual() IN ('coordenador', 'sistema'))
  WITH CHECK (organizacao_id = app.organizacao_atual()
              AND app.papel_atual() IN ('coordenador', 'sistema'));

GRANT SELECT, INSERT, UPDATE ON jobs, candidatos TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON empresas, contatos, evidencias TO authenticated;
