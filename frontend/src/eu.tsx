import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { api } from "./api/cliente";
import type { components } from "./api/schema";

export type Eu = components["schemas"]["EuOut"];

interface EstadoDoEu {
  eu: Eu | null;
  erro: string | null;
}

const ContextoDoEu = createContext<EstadoDoEu>({ eu: null, erro: null });

// Carrega quem é o usuário logado (organização e papel) uma vez por sessão.
export function ProvedorDoEu({ children }: { children: ReactNode }) {
  const [estado, setEstado] = useState<EstadoDoEu>({ eu: null, erro: null });

  useEffect(() => {
    api.GET("/eu").then(({ data, response }) => {
      if (data) setEstado({ eu: data, erro: null });
      else if (response.status === 403)
        setEstado({ eu: null, erro: "Seu usuário não tem acesso a nenhuma organização." });
      else setEstado({ eu: null, erro: "Não foi possível carregar seus dados." });
    });
  }, []);

  return <ContextoDoEu.Provider value={estado}>{children}</ContextoDoEu.Provider>;
}

export function useEu(): EstadoDoEu {
  return useContext(ContextoDoEu);
}
