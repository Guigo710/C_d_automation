import { useCallback, useEffect, useState } from "react";

import { api } from "../api/cliente";
import type { components } from "../api/schema";

type Empresa = components["schemas"]["EmpresaDaCampanhaResumo"];
type Detalhe = components["schemas"]["EmpresaDaCampanhaDetalhe"];

const STATUS_DA_FICHA: Record<string, string> = {
  preparando: "Ficha em preparo",
  pronta: "Ficha pronta",
  falhou: "Ficha não gerada",
};

const EVENTOS: Record<string, string> = {
  aprovada: "Aprovada na triagem",
  promovida: "Enviada para a operação",
  assumida: "Assumida",
  atribuida: "Atribuída",
  transferida: "Transferida",
};

export function EmpresasDaCampanha({ campanhaId, versao }: { campanhaId: string; versao: number }) {
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [aberta, setAberta] = useState<Detalhe | null>(null);

  const carregar = useCallback(async () => {
    const { data } = await api.GET("/campanhas/{campanha_id}/empresas", {
      params: { path: { campanha_id: campanhaId } },
    });
    if (data) setEmpresas(data);
  }, [campanhaId]);

  useEffect(() => {
    carregar();
  }, [carregar, versao]);

  // Enquanto houver ficha em preparo, atualiza a cada 3 segundos.
  const preparando = empresas.some((e) => e.ficha_status === "preparando");
  useEffect(() => {
    if (!preparando) return;
    const id = window.setInterval(carregar, 3000);
    return () => window.clearInterval(id);
  }, [preparando, carregar]);

  async function abrir(id: string) {
    const { data } = await api.GET("/empresas-da-campanha/{empresa_id}", {
      params: { path: { empresa_id: id } },
    });
    if (data) setAberta(data);
  }

  return (
    <section className="painel">
      <h2>Empresas na operação</h2>
      {empresas.length === 0 ? (
        <p className="suave">Nenhuma empresa enviada para os vendedores ainda.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Empresa</th>
              <th>Segmento</th>
              <th>Tier</th>
              <th>Ficha</th>
              <th>Responsável</th>
            </tr>
          </thead>
          <tbody>
            {empresas.map((e) => (
              <tr key={e.id} className="clicavel" onClick={() => abrir(e.id)}>
                <td>{e.empresa.nome_fantasia ?? e.empresa.razao_social}</td>
                <td>{e.empresa.segmento}</td>
                <td>{e.tier}</td>
                <td className="suave">{STATUS_DA_FICHA[e.ficha_status]}</td>
                <td>{e.responsavel?.nome ?? <span className="suave">sem responsável</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {aberta && (
        <div className="fundo-da-gaveta" onClick={() => setAberta(null)}>
          <aside className="gaveta" onClick={(ev) => ev.stopPropagation()}>
            <header className="cabecalho-da-pagina">
              <h2>{aberta.empresa.nome_fantasia ?? aberta.empresa.razao_social}</h2>
              <button className="link" onClick={() => setAberta(null)}>
                Fechar
              </button>
            </header>
            <p>
              <span className="etiqueta">Tier {aberta.tier}</span>{" "}
              <span className="suave">{aberta.empresa.segmento}</span>
            </p>

            <h3>Ficha de abordagem</h3>
            {aberta.ficha_status === "pronta" ? (
              <p className="ficha">{aberta.ficha}</p>
            ) : (
              <p className="suave">{STATUS_DA_FICHA[aberta.ficha_status]}</p>
            )}

            <h3>Contato</h3>
            {aberta.contato_oculto ? (
              <p className="suave">O contato aparece depois que você assumir a empresa.</p>
            ) : (
              <ul>
                {aberta.contatos.map((c) => (
                  <li key={`${c.tipo}-${c.valor}`}>
                    {c.valor} <span className="suave">({c.tipo}{c.nome ? `, ${c.nome}` : ""})</span>
                  </li>
                ))}
              </ul>
            )}

            <h3>Histórico</h3>
            <ul>
              {aberta.historico.map((h, i) => (
                <li key={i}>
                  {EVENTOS[h.tipo] ?? h.tipo}{" "}
                  <span className="suave">{new Date(h.ocorrido_em).toLocaleString("pt-BR")}</span>
                </li>
              ))}
            </ul>
          </aside>
        </div>
      )}
    </section>
  );
}
