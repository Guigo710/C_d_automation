import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { aoMudar, estaLogado } from "./autenticacao";

interface EstadoDaSessao {
  logado: boolean;
  carregando: boolean;
  // Verdadeiro quando o usuário chegou pelo link de recuperação de senha.
  recuperandoSenha: boolean;
}

const ContextoDaSessao = createContext<EstadoDaSessao>({
  logado: false,
  carregando: true,
  recuperandoSenha: false,
});

export function ProvedorDeSessao({ children }: { children: ReactNode }) {
  const [estado, setEstado] = useState<EstadoDaSessao>({
    logado: false,
    carregando: true,
    recuperandoSenha: false,
  });

  useEffect(() => {
    estaLogado().then((logado) => setEstado((atual) => ({ ...atual, logado, carregando: false })));
    return aoMudar((evento) => {
      setEstado((atual) => ({
        carregando: false,
        logado: evento !== "saiu",
        recuperandoSenha: evento === "recuperacao" ? true : evento === "saiu" ? false : atual.recuperandoSenha,
      }));
    });
  }, []);

  return <ContextoDaSessao.Provider value={estado}>{children}</ContextoDaSessao.Provider>;
}

export function useSessao(): EstadoDaSessao {
  return useContext(ContextoDaSessao);
}
