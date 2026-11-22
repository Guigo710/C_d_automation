-- Vendedor assume empresas; contato oculto até assumir (ticket 11). O RLS é a segunda
-- barreira: mesmo que a API erre, o vendedor não lê contato de empresa que não é dele.

CREATE OR REPLACE FUNCTION app.responsavel_pela_empresa(empresa uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (
    SELECT 1 FROM empresas_da_campanha ec
     WHERE ec.empresa_id = empresa AND ec.responsavel_id = app.usuario_atual()
  )
$$;
GRANT EXECUTE ON FUNCTION app.responsavel_pela_empresa(uuid) TO authenticated;

-- Contatos: coordenador, administrador e sistema veem; vendedor só das empresas que assumiu.
DROP POLICY leitura ON contatos;
CREATE POLICY leitura ON contatos FOR SELECT TO authenticated
  USING (organizacao_id = app.organizacao_atual()
         AND (app.papel_atual() IN ('administrador', 'coordenador', 'sistema')
              OR app.responsavel_pela_empresa(empresa_id)));

-- Empresas da campanha: o vendedor vê as sem responsável e as suas, nas campanhas de que
-- participa; as de outro vendedor não existem para ele.
CREATE POLICY leitura_vendedor ON empresas_da_campanha FOR SELECT TO authenticated
  USING (organizacao_id = app.organizacao_atual()
         AND app.papel_atual() = 'vendedor'
         AND app.pode_ver_campanha(campanha_id)
         AND (responsavel_id IS NULL OR responsavel_id = app.usuario_atual()));

-- Assumir: só uma empresa sem responsável, e só para si mesmo.
CREATE POLICY assumir_vendedor ON empresas_da_campanha FOR UPDATE TO authenticated
  USING (organizacao_id = app.organizacao_atual()
         AND app.papel_atual() = 'vendedor'
         AND app.pode_ver_campanha(campanha_id)
         AND responsavel_id IS NULL)
  WITH CHECK (responsavel_id = app.usuario_atual());

CREATE POLICY leitura_vendedor ON historico FOR SELECT TO authenticated
  USING (organizacao_id = app.organizacao_atual()
         AND app.papel_atual() = 'vendedor'
         AND EXISTS (SELECT 1 FROM empresas_da_campanha ec
                      WHERE ec.id = empresa_da_campanha_id
                        AND ec.responsavel_id = app.usuario_atual()));
