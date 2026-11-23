import { useEffect, useState } from "react";

import { api } from "../api/cliente";
import type { components } from "../api/schema";
import { useEu } from "../eu";
import { irPara } from "../rota";
import { NOMES_DOS_STATUS, Tier, formatarDolar, useMunicipios } from "../ui";

type Campanha = components["schemas"]["CampanhaNaLista"];

export { NOMES_DOS_STATUS };

export function Campanhas() {
  const { eu } = useEu();
  const municipios = useMunicipios();
  const [campanhas, setCampanhas] = useState<Campanha[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const ehVendedor = eu?.papel === "vendedor";

  useEffect(() => {
    api.GET("/campanhas").then(({ data }) => {
      if (data) setCampanhas(data);
      else setErro("Não foi possível carregar as campanhas.");
    });
  }, []);

  return (
    <>
      <header className="cabecalho">
        <div>
          <p className="rotulo">{ehVendedor ? "Campanhas de que você participa" : "Prospecção"}</p>
          <h1>Campanhas</h1>
        </div>
        {eu?.papel === "coordenador" && (
          <div className="acoes-do-topo">
            <button onClick={() => irPara("/campanhas/nova")}>Nova campanha</button>
          </div>
        )}
      </header>

      {erro && <p className="erro">{erro}</p>}
      {campanhas?.length === 0 && (
        <div className="painel">
          <p className="suave">
            {ehVendedor ? "Você ainda não participa de nenhuma campanha." : "Nenhuma campanha ainda."}
          </p>
        </div>
      )}

      <div className="grade-de-campanhas">
        {campanhas?.map((c) => (
          <article key={c.id} className="card-campanha" onClick={() => irPara(`/campanhas/${c.id}`)}>
            <div className="linha" style={{ justifyContent: "space-between", alignItems: "center" }}>
              <span className={`etiqueta ${c.status}`}>{NOMES_DOS_STATUS[c.status]}</span>
              <span className="chips">
                {c.tiers_alvo.map((t) => (
                  <Tier key={t} tier={t} />
                ))}
              </span>
            </div>
            <h2>{c.nome}</h2>
            <p className="suave" style={{ margin: 0 }}>
              {c.municipios_ibge.map((m) => municipios[m] ?? m).join(", ")}
            </p>
            <div className="chips">
              {c.segmentos.map((s) => (
                <span key={s} className="etiqueta">
                  {s}
                </span>
              ))}
            </div>
            {ehVendedor ? (
              <div className="metricas">
                <div>
                  <span>{c.metricas.na_operacao}</span>
                  <small>empresas</small>
                </div>
              </div>
            ) : (
              <div className="metricas">
                <div>
                  <span>{c.metricas.candidatos}</span>
                  <small>encontradas</small>
                </div>
                <div>
                  <span>{c.metricas.pendentes}</span>
                  <small>na triagem</small>
                </div>
                <div>
                  <span>{c.metricas.aprovados}</span>
                  <small>aprovadas</small>
                </div>
                <div>
                  <span>{c.metricas.na_operacao}</span>
                  <small>na operação</small>
                </div>
              </div>
            )}
            {!ehVendedor && (
              <p className="suave mono" style={{ margin: 0, fontSize: "0.8rem" }}>
                gasto {formatarDolar(c.metricas.gasto_usd)} de {formatarDolar(c.teto_gasto_usd)} · limite{" "}
                {c.limite_empresas} empresas
              </p>
            )}
          </article>
        ))}
      </div>
    </>
  );
}
