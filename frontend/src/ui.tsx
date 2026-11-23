import { useEffect, useState, type ReactNode } from "react";

import { api } from "./api/cliente";

export const NOMES_DOS_PAPEIS: Record<string, string> = {
  administrador: "Administrador",
  coordenador: "Coordenador",
  vendedor: "Vendedor",
};

export const NOMES_DOS_STATUS: Record<string, string> = {
  rascunho: "Rascunho",
  ativa: "Ativa",
  pausada: "Pausada",
  encerrada: "Encerrada",
};

export const MOTIVOS_DE_RECUSA: Record<string, string> = {
  fora_do_perfil: "Fora do perfil",
  cnpj_inativo: "CNPJ inativo",
  fora_da_regiao: "Fora da região",
  dados_incompletos: "Dados incompletos",
  ja_e_cliente: "Já é cliente",
  duplicado: "Duplicado",
  opt_out: "Não quer contato",
};

export const NOMES_DAS_FONTES: Record<string, string> = {
  receita: "Receita",
  google_places: "Maps",
  site: "Site",
  brave: "Busca",
};

export function formatarCnpj(cnpj: string): string {
  return cnpj.length === 14
    ? `${cnpj.slice(0, 2)}.${cnpj.slice(2, 5)}.${cnpj.slice(5, 8)}/${cnpj.slice(8, 12)}-${cnpj.slice(12)}`
    : cnpj;
}

export function formatarDolar(valor: string | number): string {
  return `US$ ${Number(valor).toFixed(2)}`;
}

export function Tier({ tier }: { tier: string | null | undefined }) {
  return <span className={`tier ${tier ?? ""}`}>{tier ?? "–"}</span>;
}

export function BarraDeNota({ nota }: { nota: number | null | undefined }) {
  return (
    <div className="barra-de-nota" aria-label={`Nota ${nota ?? "sem nota"}`}>
      <div className="trilho">
        <div className="preenchido" style={{ width: `${nota ?? 0}%` }} />
      </div>
      <span className="valor">{nota ?? "–"}</span>
    </div>
  );
}

export function Kpi({ rotulo, valor, destaque }: { rotulo: string; valor: ReactNode; destaque?: boolean }) {
  return (
    <div className={`kpi${destaque ? " destaque" : ""}`}>
      <p className="rotulo">{rotulo}</p>
      <span className="valor">{valor}</span>
    </div>
  );
}

export function Gaveta({
  titulo,
  subtitulo,
  aoFechar,
  children,
}: {
  titulo: ReactNode;
  subtitulo?: ReactNode;
  aoFechar: () => void;
  children: ReactNode;
}) {
  useEffect(() => {
    const aoTeclar = (e: KeyboardEvent) => e.key === "Escape" && aoFechar();
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [aoFechar]);

  return (
    <div className="fundo-da-gaveta" onClick={aoFechar}>
      <aside className="gaveta" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <header>
          <div>
            <h2>{titulo}</h2>
            {subtitulo && <p className="suave">{subtitulo}</p>}
          </div>
          <button className="link" onClick={aoFechar} aria-label="Fechar">
            Fechar ✕
          </button>
        </header>
        {children}
      </aside>
    </div>
  );
}

// Nomes dos municípios atendidos pela organização, para mostrar cidade em vez de código IBGE.
let cacheDeMunicipios: Promise<Record<string, string>> | null = null;

export function useMunicipios(): Record<string, string> {
  const [mapa, setMapa] = useState<Record<string, string>>({});
  useEffect(() => {
    cacheDeMunicipios ??= api
      .GET("/municipios-atendidos")
      .then(({ data }) => Object.fromEntries((data ?? []).map((m) => [m.municipio_ibge, m.nome])));
    cacheDeMunicipios.then(setMapa);
  }, []);
  return mapa;
}
