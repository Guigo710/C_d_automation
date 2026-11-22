-- Operação (ticket 09): empresas promovidas para os vendedores, ficha de abordagem,
-- idempotência da promoção e histórico de cada empresa.

CREATE TABLE empresas_da_campanha (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organizacao_id  uuid NOT NULL DEFAULT app.organizacao_atual() REFERENCES organizacoes(id),
  campanha_id     uuid NOT NULL REFERENCES campanhas(id),
  empresa_id      uuid NOT NULL REFERENCES empresas(id),
  candidato_id    uuid NOT NULL UNIQUE REFERENCES candidatos(id),
  tier            char(1) NOT NULL CHECK (tier IN ('A', 'B', 'C')),
  nota_total      smallint,
  responsavel_id  uuid REFERENCES perfis(usuario_id),
  ficha           text,
  ficha_fatos     jsonb NOT NULL DEFAULT '[]'::jsonb,
  ficha_status    text NOT NULL DEFAULT 'preparando'
                  CHECK (ficha_status IN ('preparando', 'pronta', 'falhou')),
  ficha_gerada_em timestamptz,
  promovida_por   uuid DEFAULT app.usuario_atual(),
  promovida_em    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (campanha_id, empresa_id)
);
CREATE INDEX empresas_da_campanha_campanha_idx ON empresas_da_campanha (campanha_id, tier);
CREATE INDEX empresas_da_campanha_responsavel_idx ON empresas_da_campanha (responsavel_id);

-- Um clique de "subir para operação" = uma chave; repetir a chave devolve o mesmo resultado.
CREATE TABLE promocoes (
  organizacao_id uuid NOT NULL DEFAULT app.organizacao_atual() REFERENCES organizacoes(id),
  chave          text NOT NULL,
  campanha_id    uuid NOT NULL REFERENCES campanhas(id),
  resultado      jsonb,
  criada_em      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organizacao_id, chave)
);

-- Histórico da empresa (timeline da gaveta). Só aceita inclusões.
CREATE TABLE historico (
  id                    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  organizacao_id        uuid NOT NULL DEFAULT app.organizacao_atual() REFERENCES organizacoes(id),
  empresa_da_campanha_id uuid NOT NULL REFERENCES empresas_da_campanha(id),
  tipo                  text NOT NULL
                        CHECK (tipo IN ('aprovada', 'promovida', 'assumida', 'atribuida', 'transferida')),
  por_usuario           uuid,
  de_usuario            uuid,
  para_usuario          uuid,
  detalhes              jsonb NOT NULL DEFAULT '{}'::jsonb,
  ocorrido_em           timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX historico_empresa_idx ON historico (empresa_da_campanha_id, ocorrido_em);

CREATE TRIGGER historico_sem_alteracao
  BEFORE UPDATE OR DELETE ON historico
  FOR EACH ROW EXECUTE FUNCTION app.auditoria_imutavel();

ALTER TABLE empresas_da_campanha ENABLE ROW LEVEL SECURITY;
ALTER TABLE promocoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE historico ENABLE ROW LEVEL SECURITY;

CREATE POLICY leitura ON empresas_da_campanha FOR SELECT TO authenticated
  USING (organizacao_id = app.organizacao_atual()
         AND app.papel_atual() IN ('administrador', 'coordenador', 'sistema'));
CREATE POLICY inclusao ON empresas_da_campanha FOR INSERT TO authenticated
  WITH CHECK (organizacao_id = app.organizacao_atual() AND app.papel_atual() = 'coordenador');
CREATE POLICY atualizacao ON empresas_da_campanha FOR UPDATE TO authenticated
  USING (organizacao_id = app.organizacao_atual()
         AND app.papel_atual() IN ('coordenador', 'sistema'));

CREATE POLICY coordenador ON promocoes FOR ALL TO authenticated
  USING (organizacao_id = app.organizacao_atual() AND app.papel_atual() = 'coordenador')
  WITH CHECK (organizacao_id = app.organizacao_atual() AND app.papel_atual() = 'coordenador');

CREATE POLICY leitura ON historico FOR SELECT TO authenticated
  USING (organizacao_id = app.organizacao_atual()
         AND app.papel_atual() IN ('administrador', 'coordenador'));
CREATE POLICY inclusao ON historico FOR INSERT TO authenticated
  WITH CHECK (organizacao_id = app.organizacao_atual());

GRANT SELECT, INSERT, UPDATE ON empresas_da_campanha, promocoes TO authenticated;
GRANT SELECT, INSERT ON historico TO authenticated;
