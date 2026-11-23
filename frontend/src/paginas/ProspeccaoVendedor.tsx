import { useCallback, useEffect, useState } from "react";

import { api } from "../api/cliente";
import type { components } from "../api/schema";
import { useEu } from "../eu";
import { BarraDeNota, Tier, useMunicipios } from "../ui";
import { GavetaDaEmpresa } from "./GavetaDaEmpresa";

type Empresa = components["schemas"]["EmpresaDaCampanhaResumo"];
type Filtro = "todas" | "livres" | "minhas";

export function ProspeccaoVendedor({ campanhaId }: { campanhaId: string }) {
  const { eu } = useEu();
  const municipios = useMunicipios();
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [filtro, setFiltro] = useState<Filtro>("todas");
  const [aberta, setAberta] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    const { data } = await api.GET("/campanhas/{campanha_id}/empresas", {
      params: { path: { campanha_id: campanhaId } },
    });
    if (data) setEmpresas(data);
  }, [campanhaId]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const cidade = (codigo: string | null | undefined) => (codigo ? (municipios[codigo] ?? codigo) : "–");
  const minha = (e: Empresa) => e.responsavel?.id === eu?.usuario_id;
  const visiveis = empresas.filter((e) =>
    filtro === "livres" ? !e.responsavel : filtro === "minhas" ? minha(e) : true,
  );

  return (
    <>
      <header className="cabecalho">
        <div>
          <p className="rotulo">Empresas aprovadas da campanha</p>
          <h1>Prospecção</h1>
        </div>
      </header>

      <div className="barra-de-filtros">
        <div className="alternador" role="group" aria-label="Filtrar">
          {(
            [
              ["todas", `Todas (${empresas.length})`],
              ["livres", `Sem responsável (${empresas.filter((e) => !e.responsavel).length})`],
              ["minhas", `Minhas (${empresas.filter(minha).length})`],
            ] as [Filtro, string][]
          ).map(([valor, nome]) => (
            <button key={valor} className={filtro === valor ? "ativo" : ""} onClick={() => setFiltro(valor)}>
              {nome}
            </button>
          ))}
        </div>
        <span className="suave">O contato aparece depois que você assume a empresa.</span>
      </div>

      {empresas.length === 0 ? (
        <div className="painel">
          <p className="suave">O coordenador ainda não liberou empresas nesta campanha.</p>
        </div>
      ) : (
        <div className="kanban tres">
          {(["A", "B", "C"] as const).map((tier) => {
            const lista = visiveis.filter((e) => e.tier === tier);
            return (
              <section key={tier} className="coluna">
                <header>
                  <Tier tier={tier} />
                  <h3>Tier {tier}</h3>
                  <span className="mono suave">{lista.length}</span>
                </header>
                {lista.map((e) => (
                  <article key={e.id} className={`card-empresa ${e.tier}`} onClick={() => setAberta(e.id)}>
                    <header>
                      <strong>{e.empresa.nome_fantasia ?? e.empresa.razao_social}</strong>
                    </header>
                    <p className="meta">
                      {cidade(e.empresa.municipio_ibge)} · {e.empresa.segmento}
                    </p>
                    <BarraDeNota nota={e.nota_total} />
                    <div className="rodape-card">
                      {minha(e) ? (
                        <span className="etiqueta sucesso">minha</span>
                      ) : e.responsavel ? (
                        <span className="etiqueta">com {e.responsavel.nome}</span>
                      ) : (
                        <span className="etiqueta alerta">livre</span>
                      )}
                      {e.ficha_status === "pronta" && <span className="etiqueta">ficha pronta</span>}
                    </div>
                  </article>
                ))}
              </section>
            );
          })}
        </div>
      )}

      {aberta && (
        <GavetaDaEmpresa empresaId={aberta} cidade={cidade} aoFechar={() => setAberta(null)} aoMudar={carregar} />
      )}
    </>
  );
}
