import { useEffect, useState } from "react";

import { api } from "../api/cliente";
import type { components } from "../api/schema";
import { supabase } from "../supabase";

type Eu = components["schemas"]["EuOut"];

const NOMES_DOS_PAPEIS: Record<string, string> = {
  administrador: "Administrador",
  coordenador: "Coordenador",
  vendedor: "Vendedor",
};

export function MinhaOrganizacao() {
  const [eu, setEu] = useState<Eu | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    api.GET("/eu").then(({ data, response }) => {
      if (data) setEu(data);
      else if (response.status === 403) setErro("Seu usuário não tem acesso a nenhuma organização.");
      else setErro("Não foi possível carregar seus dados.");
    });
  }, []);

  return (
    <main className="cartao">
      {erro && <p className="erro">{erro}</p>}
      {!erro && !eu && <p>Carregando...</p>}
      {eu && (
        <>
          <p className="rotulo">Organização</p>
          <h1>{eu.organizacao.nome}</h1>
          <dl>
            <dt>Usuário</dt>
            <dd>{eu.nome}</dd>
            <dt>E-mail</dt>
            <dd>{eu.email}</dd>
            <dt>Papel</dt>
            <dd>{NOMES_DOS_PAPEIS[eu.papel] ?? eu.papel}</dd>
          </dl>
        </>
      )}
      <button className="link" onClick={() => supabase.auth.signOut()}>
        Sair
      </button>
    </main>
  );
}
