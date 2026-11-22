import type { Session } from "@supabase/supabase-js";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { supabase } from "./supabase";

interface EstadoDaSessao {
  sessao: Session | null;
  carregando: boolean;
  // Verdadeiro quando o usuário chegou pelo link de recuperação de senha.
  recuperandoSenha: boolean;
}

const ContextoDaSessao = createContext<EstadoDaSessao>({
  sessao: null,
  carregando: true,
  recuperandoSenha: false,
});

export function ProvedorDeSessao({ children }: { children: ReactNode }) {
  const [estado, setEstado] = useState<EstadoDaSessao>({
    sessao: null,
    carregando: true,
    recuperandoSenha: false,
  });

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setEstado((atual) => ({ ...atual, sessao: data.session, carregando: false }));
    });
    const { data } = supabase.auth.onAuthStateChange((evento, sessao) => {
      setEstado((atual) => ({
        sessao,
        carregando: false,
        recuperandoSenha:
          evento === "PASSWORD_RECOVERY" ? true : evento === "SIGNED_OUT" ? false : atual.recuperandoSenha,
      }));
    });
    return () => data.subscription.unsubscribe();
  }, []);

  return <ContextoDaSessao.Provider value={estado}>{children}</ContextoDaSessao.Provider>;
}

export function useSessao(): EstadoDaSessao {
  return useContext(ContextoDaSessao);
}
