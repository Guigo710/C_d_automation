import { useEffect, useState } from "react";

// Navegação simples por hash (#/campanhas, #/campanhas/nova, #/campanhas/<id>).
export function useRota(): string {
  const [rota, setRota] = useState(() => window.location.hash.slice(1) || "/");
  useEffect(() => {
    const aoMudar = () => setRota(window.location.hash.slice(1) || "/");
    window.addEventListener("hashchange", aoMudar);
    return () => window.removeEventListener("hashchange", aoMudar);
  }, []);
  return rota;
}

export function irPara(rota: string): void {
  window.location.hash = rota;
}
