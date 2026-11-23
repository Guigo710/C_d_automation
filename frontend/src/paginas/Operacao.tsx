import { useCallback, useEffect, useState } from "react";

import { api } from "../api/cliente";
import type { components } from "../api/schema";
import { Kpi, Tier, useMunicipios } from "../ui";
import { GavetaDaEmpresa, STATUS_DA_FICHA } from "./GavetaDaEmpresa";

type Empresa = components["schemas"]["EmpresaDaCampanhaResumo"];
type Filtro = "todas" | "livres" | "atribuidas";

export function Operacao({ campanhaId }: { campanhaId: string }) {
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

  const preparando = empresas.some((e) => e.ficha_status === "preparando");
  useEffect(() => {
    if (!preparando) return;
    const id = window.setInterval(carregar, 2000);
    return () => window.clearInterval(id);
  }, [preparando, carregar]);

  const cidade = (codigo: string | null | undefined) => (codigo ? (municipios[codigo] ?? codigo) : "–");
  const livres = empresas.filter((e) => !e.responsavel);
  const visiveis =
    filtro === "livres" ? livres : filtro === "atribuidas" ? empresas.filter((e) => e.responsavel) : empresas;

  return (
    <>
      <header className="cabecalho">
        <div>
          <p className="rotulo">Empresas com os vendedores</p>
          <h1>Operação</h1>
        </div>
      </header>

      <div className="kpis">
        <Kpi rotulo="Na operação" valor={empresas.length} destaque />
        <Kpi rotulo="Sem responsável" valor={livres.length} />
        <Kpi rotulo="Com vendedor" valor={empresas.length - livres.length} />
        <Kpi rotulo="Fichas prontas" valor={empresas.filter((e) => e.ficha_status === "pronta").length} />
      </div>

      <div className="barra-de-filtros">
        <div className="alternador" role="group" aria-label="Filtrar">
          {(
            [
              ["todas", "Todas"],
              ["livres", "Sem responsável"],
              ["atribuidas", "Com vendedor"],
            ] as [Filtro, string][]
          ).map(([valor, nome]) => (
            <button key={valor} className={filtro === valor ? "ativo" : ""} onClick={() => setFiltro(valor)}>
              {nome}
            </button>
          ))}
        </div>
      </div>

      <section className="painel">
        {visiveis.length === 0 ? (
          <p className="suave">
            Nenhuma empresa aqui. Aprove candidatos na Triagem e use "Subir para operação".
          </p>
        ) : (
          <div className="tabela-rolavel">
            <table>
              <thead>
                <tr>
                  <th>Tier</th>
                  <th>Empresa</th>
                  <th>Cidade</th>
                  <th>Segmento</th>
                  <th className="numero">Nota</th>
                  <th>Ficha</th>
                  <th>Responsável</th>
                </tr>
              </thead>
              <tbody>
                {visiveis.map((e) => (
                  <tr key={e.id} className="clicavel" onClick={() => setAberta(e.id)}>
                    <td>
                      <Tier tier={e.tier} />
                    </td>
                    <td>{e.empresa.nome_fantasia ?? e.empresa.razao_social}</td>
                    <td>{cidade(e.empresa.municipio_ibge)}</td>
                    <td>{e.empresa.segmento}</td>
                    <td className="numero">{e.nota_total ?? "–"}</td>
                    <td className="suave">{STATUS_DA_FICHA[e.ficha_status]}</td>
                    <td>{e.responsavel?.nome ?? <span className="suave">sem responsável</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {aberta && (
        <GavetaDaEmpresa empresaId={aberta} cidade={cidade} aoFechar={() => setAberta(null)} aoMudar={carregar} />
      )}
    </>
  );
}
