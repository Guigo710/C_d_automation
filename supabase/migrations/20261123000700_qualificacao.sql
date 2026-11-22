-- Qualificação dos candidatos (ticket 07): exclusões por regra, notas, tier e cache da IA.

ALTER TABLE candidatos
  ADD COLUMN nota_aderencia     smallint CHECK (nota_aderencia BETWEEN 0 AND 100),
  ADD COLUMN nota_potencial     smallint CHECK (nota_potencial BETWEEN 0 AND 100),
  ADD COLUMN nota_geografia     smallint CHECK (nota_geografia BETWEEN 0 AND 100),
  ADD COLUMN nota_dados         smallint CHECK (nota_dados BETWEEN 0 AND 100),
  ADD COLUMN nota_total         smallint CHECK (nota_total BETWEEN 0 AND 100),
  ADD COLUMN tier_sugerido      char(1) CHECK (tier_sugerido IN ('A', 'B', 'C')),
  ADD COLUMN tier_final         char(1) CHECK (tier_final IN ('A', 'B', 'C')),
  ADD COLUMN motivo_recusa      text CHECK (motivo_recusa IN (
                                  'fora_do_perfil', 'cnpj_inativo', 'fora_da_regiao',
                                  'dados_incompletos', 'ja_e_cliente', 'duplicado', 'opt_out')),
  ADD COLUMN recusa_sugerida    boolean NOT NULL DEFAULT false,
  ADD COLUMN justificativas     jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN lacunas            text[] NOT NULL DEFAULT '{}',
  ADD COLUMN confianca          numeric(3, 2) CHECK (confianca BETWEEN 0 AND 1),
  ADD COLUMN baixa_confianca    boolean NOT NULL DEFAULT false,
  ADD COLUMN em_revisao         boolean NOT NULL DEFAULT false,
  ADD COLUMN motivo_revisao     text,
  ADD COLUMN modelo             text,
  ADD COLUMN versao_prompt      text,
  ADD COLUMN versao_regras      integer,
  ADD COLUMN qualificado_em     timestamptz,
  -- Recusa sempre com motivo (sugerida pela regra ou decidida pelo coordenador).
  ADD CONSTRAINT recusa_com_motivo CHECK (status <> 'recusado' OR motivo_recusa IS NOT NULL);

ALTER TABLE contatos
  ADD COLUMN status_validacao text CHECK (status_validacao IN ('valido', 'invalido', 'risco'));

-- Respostas da IA já pagas, por hash de (modelo, versão do prompt, entrada).
CREATE TABLE llm_cache (
  organizacao_id uuid NOT NULL DEFAULT app.organizacao_atual() REFERENCES organizacoes(id),
  hash           text NOT NULL,
  modelo         text NOT NULL,
  resposta       jsonb NOT NULL,
  criado_em      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organizacao_id, hash)
);

ALTER TABLE llm_cache ENABLE ROW LEVEL SECURITY;
CREATE POLICY sistema ON llm_cache FOR ALL TO authenticated
  USING (organizacao_id = app.organizacao_atual() AND app.papel_atual() = 'sistema')
  WITH CHECK (organizacao_id = app.organizacao_atual() AND app.papel_atual() = 'sistema');
GRANT SELECT, INSERT ON llm_cache TO authenticated;
