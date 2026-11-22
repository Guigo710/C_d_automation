import { useEffect, useState } from "react";

import { api } from "../api/cliente";
import type { components } from "../api/schema";
import { useEu } from "../eu";
import { irPara } from "../rota";

type Campanha = components["schemas"]["CampanhaResumo"];

export const NOMES_DOS_STATUS: Record<string, string> = {
  rascunho: "Rascunho",
  ativa: "Ativa",
  pausada: "Pausada",
  encerrada: "Encerrada",
};

export function Campanhas() {
  const { eu } = useEu();
  const [campanhas, setCampanhas] = useState<Campanha[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    api.GET("/campanhas").then(({ data }) => {
      if (data) setCampanhas(data);
      else setErro("Não foi possível carregar as campanhas.");
    });
  }, []);

  return (
    <section className="painel">
      <header className="cabecalho-da-pagina">
        <h1>Campanhas</h1>
        {eu?.papel === "coordenador" && (
          <button onClick={() => irPara("/campanhas/nova")}>Nova campanha</button>
        )}
      </header>
      {erro && <p className="erro">{erro}</p>}
      {campanhas && campanhas.length === 0 && <p>Nenhuma campanha ainda.</p>}
      {campanhas && campanhas.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Nome</th>
              <th>Status</th>
              <th className="numero">Limite de empresas</th>
              <th className="numero">Teto (US$)</th>
            </tr>
          </thead>
          <tbody>
            {campanhas.map((c) => (
              <tr key={c.id} className="clicavel" onClick={() => irPara(`/campanhas/${c.id}`)}>
                <td>{c.nome}</td>
                <td>
                  <span className={`etiqueta ${c.status}`}>{NOMES_DOS_STATUS[c.status]}</span>
                </td>
                <td className="numero">{c.limite_empresas}</td>
                <td className="numero">{c.teto_gasto_usd}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
