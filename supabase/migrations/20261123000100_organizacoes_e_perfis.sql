-- Organizações, perfis de usuário e a base do isolamento por organização (ADRs 0001-0003).
--
-- A API conecta como dono das tabelas, lê o perfil do usuário e, antes de qualquer
-- consulta de negócio, faz SET LOCAL ROLE authenticated e grava as claims da requisição.
-- A partir daí o RLS abaixo restringe tudo à organização do usuário.

CREATE SCHEMA IF NOT EXISTS app;

-- Organização da requisição atual, lida das claims gravadas pela API (ou pelo Supabase).
CREATE OR REPLACE FUNCTION app.organizacao_atual() RETURNS uuid
LANGUAGE sql STABLE AS $$
  SELECT nullif(current_setting('request.jwt.claims', true)::jsonb ->> 'organizacao_id', '')::uuid
$$;

-- Papel da requisição atual: 'administrador', 'coordenador' ou 'vendedor'.
CREATE OR REPLACE FUNCTION app.papel_atual() RETURNS text
LANGUAGE sql STABLE AS $$
  SELECT nullif(current_setting('request.jwt.claims', true)::jsonb ->> 'papel', '')
$$;

GRANT USAGE ON SCHEMA app TO authenticated;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA app TO authenticated;

CREATE TABLE organizacoes (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nome       text NOT NULL,
  criada_em  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE perfis (
  usuario_id     uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  organizacao_id uuid NOT NULL REFERENCES organizacoes(id),
  nome           text NOT NULL,
  email          text NOT NULL,
  papel          text NOT NULL CHECK (papel IN ('administrador', 'coordenador', 'vendedor')),
  ativo          boolean NOT NULL DEFAULT true,
  criado_em      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX perfis_organizacao_idx ON perfis (organizacao_id);

ALTER TABLE organizacoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE perfis ENABLE ROW LEVEL SECURITY;

CREATE POLICY organizacoes_da_propria ON organizacoes
  FOR SELECT TO authenticated
  USING (id = app.organizacao_atual());

CREATE POLICY perfis_da_propria ON perfis
  FOR SELECT TO authenticated
  USING (organizacao_id = app.organizacao_atual());

GRANT SELECT ON organizacoes, perfis TO authenticated;

-- Hook de token do Supabase Auth: coloca organizacao_id e papel no token a partir do
-- perfil. O usuário nunca escolhe esses valores. Sem perfil ativo, as claims saem vazias.
CREATE OR REPLACE FUNCTION public.custom_access_token_hook(event jsonb) RETURNS jsonb
LANGUAGE plpgsql STABLE AS $$
DECLARE
  claims jsonb := coalesce(event -> 'claims', '{}'::jsonb);
  perfil record;
BEGIN
  SELECT p.organizacao_id, p.papel INTO perfil
    FROM public.perfis p
   WHERE p.usuario_id = (event ->> 'user_id')::uuid
     AND p.ativo;

  claims := claims - 'organizacao_id' - 'papel';
  IF FOUND THEN
    claims := claims
      || jsonb_build_object('organizacao_id', perfil.organizacao_id, 'papel', perfil.papel);
  END IF;

  RETURN jsonb_set(event, '{claims}', claims);
END;
$$;

GRANT USAGE ON SCHEMA public TO supabase_auth_admin;
GRANT EXECUTE ON FUNCTION public.custom_access_token_hook(jsonb) TO supabase_auth_admin;
REVOKE EXECUTE ON FUNCTION public.custom_access_token_hook(jsonb) FROM authenticated, anon, public;
GRANT SELECT ON public.perfis TO supabase_auth_admin;
CREATE POLICY perfis_leitura_hook ON perfis
  FOR SELECT TO supabase_auth_admin
  USING (true);
