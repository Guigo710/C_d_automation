import { useCallback, useEffect, useState } from "react";

import { api } from "../api/cliente";
import type { components } from "../api/schema";
import { Kpi, Tier, useMunicipios } from "../ui";
import { GavetaDaEmpresa, STATUS_DA_FICHA } from "./GavetaDaEmpresa";

type Empresa = components["schemas"]["EmpresaDaCampanhaResumo"];

export function Clientes() {
  const municipios = useMunicipios();
  const [empresas, setEmpresas] = useState<Empresa[] | null>(null);
  const [aberta, setAberta] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    const { data } = await api.GET("/minhas-empresas");
    setEmpresas(data ?? []);
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const cidade = (codigo: string | null | undefined) => (codigo ? (municipios[codigo] ?? codigo) : "–");
  const lista = empresas ?? [];

  return (
    <>
      <header className="cabecalho">
        <div>
          <p className="rotulo">Empresas sob sua responsabilidade</p>
          <h1>Meus clientes</h1>
        </div>
      </header>

      <div className="kpis">
        <Kpi rotulo="Minhas empresas" valor={lista.length} destaque />
        <Kpi rotulo="Tier A" valor={lista.filter((e) => e.tier === "A").length} />
        <Kpi rotulo="Tier B" valor={lista.filter((e) => e.tier === "B").length} />
        <Kpi rotulo="Tier C" valor={lista.filter((e) => e.tier === "C").length} />
      </div>

      <section className="painel">
        {empresas && lista.length === 0 ? (
          <p className="suave">Você ainda não assumiu nenhuma empresa. Veja as disponíveis na prospecção da campanha.</p>
        ) : (
          <div className="tabela-rolavel">
            <table>
              <thead>
                <tr>
                  <th>Tier</th>
                  <th>Empresa</th>
                  <th>Cidade</th>
                  <th>Segmento</th>
                  <th>Campanha</th>
                  <th>Ficha</th>
                </tr>
              </thead>
              <tbody>
                {lista.map((e) => (
                  <tr key={e.id} className="clicavel" onClick={() => setAberta(e.id)}>
                    <td>
                      <Tier tier={e.tier} />
                    </td>
                    <td>{e.empresa.nome_fantasia ?? e.empresa.razao_social}</td>
                    <td>{cidade(e.empresa.municipio_ibge)}</td>
                    <td>{e.empresa.segmento}</td>
                    <td className="suave">{e.campanha_nome}</td>
                    <td className="suave">{STATUS_DA_FICHA[e.ficha_status]}</td>
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
