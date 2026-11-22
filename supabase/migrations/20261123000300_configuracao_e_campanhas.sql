-- Configuração da organização (semeada sem tela na v0) e campanhas (ticket 03, ADR 0005).

CREATE OR REPLACE FUNCTION app.usuario_atual() RETURNS uuid
LANGUAGE sql STABLE AS $$
  SELECT nullif(current_setting('request.jwt.claims', true)::jsonb ->> 'sub', '')::uuid
$$;
GRANT EXECUTE ON FUNCTION app.usuario_atual() TO authenticated;

-- Regras da organização, versionadas: cada alteração cria uma nova versão.
CREATE TABLE configuracoes_organizacao (
  organizacao_id uuid NOT NULL REFERENCES organizacoes(id),
  versao         integer NOT NULL CHECK (versao > 0),
  perfil_ideal   text NOT NULL,
  pesos          jsonb NOT NULL DEFAULT
                   '{"aderencia": 40, "potencial": 25, "geografia": 20, "dados": 15}'::jsonb,
  cortes         jsonb NOT NULL DEFAULT '{"A": 80, "B": 60, "C": 40}'::jsonb,
  criada_em      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organizacao_id, versao)
);

CREATE TABLE catalogo_segmentos (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organizacao_id uuid NOT NULL REFERENCES organizacoes(id),
  nome           text NOT NULL,
  cnaes          char(7)[] NOT NULL CHECK (cardinality(cnaes) > 0),
  UNIQUE (organizacao_id, nome)
);

CREATE TABLE municipios_atendidos (
  organizacao_id uuid NOT NULL REFERENCES organizacoes(id),
  municipio_ibge char(7) NOT NULL CHECK (municipio_ibge ~ '^[0-9]{7}$'),
  nome           text NOT NULL,
  uf             char(2) NOT NULL,
  tem_rota       boolean NOT NULL DEFAULT false,
  PRIMARY KEY (organizacao_id, municipio_ibge)
);

CREATE TABLE clientes_atuais (
  organizacao_id uuid NOT NULL REFERENCES organizacoes(id),
  cnpj           char(14) NOT NULL CHECK (cnpj ~ '^[0-9A-Z]{12}[0-9]{2}$'),
  PRIMARY KEY (organizacao_id, cnpj)
);

CREATE TABLE lista_bloqueio (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organizacao_id uuid NOT NULL REFERENCES organizacoes(id),
  tipo           text NOT NULL CHECK (tipo IN ('cnpj', 'email', 'telefone', 'dominio')),
  valor          text NOT NULL,
  criado_em      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organizacao_id, tipo, valor)
);

CREATE TABLE campanhas (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organizacao_id  uuid NOT NULL DEFAULT app.organizacao_atual() REFERENCES organizacoes(id),
  nome            text NOT NULL,
  status          text NOT NULL DEFAULT 'rascunho'
                  CHECK (status IN ('rascunho', 'ativa', 'pausada', 'encerrada')),
  municipios_ibge char(7)[] NOT NULL CHECK (cardinality(municipios_ibge) > 0),
  tiers_alvo      char(1)[] NOT NULL DEFAULT '{A,B,C}'
                  CHECK (cardinality(tiers_alvo) > 0 AND tiers_alvo <@ '{A,B,C}'::char(1)[]),
  limite_empresas integer NOT NULL CHECK (limite_empresas > 0),
  teto_gasto_usd  numeric(10, 2) NOT NULL CHECK (teto_gasto_usd >= 0),
  criada_por      uuid NOT NULL DEFAULT app.usuario_atual(),
  criada_em       timestamptz NOT NULL DEFAULT now(),
  atualizada_em   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX campanhas_organizacao_idx ON campanhas (organizacao_id, criada_em DESC);

CREATE TABLE campanha_segmentos (
  campanha_id    uuid NOT NULL REFERENCES campanhas(id) ON DELETE CASCADE,
  segmento_id    uuid NOT NULL REFERENCES catalogo_segmentos(id),
  organizacao_id uuid NOT NULL DEFAULT app.organizacao_atual() REFERENCES organizacoes(id),
  PRIMARY KEY (campanha_id, segmento_id)
);

CREATE TABLE campanha_membros (
  campanha_id    uuid NOT NULL REFERENCES campanhas(id) ON DELETE CASCADE,
  usuario_id     uuid NOT NULL REFERENCES perfis(usuario_id),
  organizacao_id uuid NOT NULL DEFAULT app.organizacao_atual() REFERENCES organizacoes(id),
  PRIMARY KEY (campanha_id, usuario_id)
);
CREATE INDEX campanha_membros_usuario_idx ON campanha_membros (usuario_id);

-- Vendedor só enxerga campanhas de que é membro.
CREATE OR REPLACE FUNCTION app.pode_ver_campanha(campanha uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT app.papel_atual() IN ('administrador', 'coordenador')
      OR EXISTS (
           SELECT 1 FROM campanha_membros m
            WHERE m.campanha_id = campanha AND m.usuario_id = app.usuario_atual()
         )
$$;
GRANT EXECUTE ON FUNCTION app.pode_ver_campanha(uuid) TO authenticated;

ALTER TABLE configuracoes_organizacao ENABLE ROW LEVEL SECURITY;
ALTER TABLE catalogo_segmentos ENABLE ROW LEVEL SECURITY;
ALTER TABLE municipios_atendidos ENABLE ROW LEVEL SECURITY;
ALTER TABLE clientes_atuais ENABLE ROW LEVEL SECURITY;
ALTER TABLE lista_bloqueio ENABLE ROW LEVEL SECURITY;
ALTER TABLE campanhas ENABLE ROW LEVEL SECURITY;
ALTER TABLE campanha_segmentos ENABLE ROW LEVEL SECURITY;
ALTER TABLE campanha_membros ENABLE ROW LEVEL SECURITY;

CREATE POLICY leitura ON configuracoes_organizacao FOR SELECT TO authenticated
  USING (organizacao_id = app.organizacao_atual());
CREATE POLICY leitura ON catalogo_segmentos FOR SELECT TO authenticated
  USING (organizacao_id = app.organizacao_atual());
CREATE POLICY leitura ON municipios_atendidos FOR SELECT TO authenticated
  USING (organizacao_id = app.organizacao_atual());
CREATE POLICY leitura ON clientes_atuais FOR SELECT TO authenticated
  USING (organizacao_id = app.organizacao_atual());
CREATE POLICY leitura ON lista_bloqueio FOR SELECT TO authenticated
  USING (organizacao_id = app.organizacao_atual());

CREATE POLICY leitura ON campanhas FOR SELECT TO authenticated
  USING (organizacao_id = app.organizacao_atual() AND app.pode_ver_campanha(id));
CREATE POLICY escrita_coordenador ON campanhas FOR ALL TO authenticated
  USING (organizacao_id = app.organizacao_atual() AND app.papel_atual() = 'coordenador')
  WITH CHECK (organizacao_id = app.organizacao_atual() AND app.papel_atual() = 'coordenador');

CREATE POLICY leitura ON campanha_segmentos FOR SELECT TO authenticated
  USING (organizacao_id = app.organizacao_atual() AND app.pode_ver_campanha(campanha_id));
CREATE POLICY escrita_coordenador ON campanha_segmentos FOR ALL TO authenticated
  USING (organizacao_id = app.organizacao_atual() AND app.papel_atual() = 'coordenador')
  WITH CHECK (organizacao_id = app.organizacao_atual() AND app.papel_atual() = 'coordenador');

CREATE POLICY leitura ON campanha_membros FOR SELECT TO authenticated
  USING (organizacao_id = app.organizacao_atual() AND app.pode_ver_campanha(campanha_id));
CREATE POLICY escrita_coordenador ON campanha_membros FOR ALL TO authenticated
  USING (organizacao_id = app.organizacao_atual() AND app.papel_atual() = 'coordenador')
  WITH CHECK (organizacao_id = app.organizacao_atual() AND app.papel_atual() = 'coordenador');

GRANT SELECT ON configuracoes_organizacao, catalogo_segmentos, municipios_atendidos,
  clientes_atuais, lista_bloqueio TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON campanhas, campanha_segmentos, campanha_membros
  TO authenticated;
