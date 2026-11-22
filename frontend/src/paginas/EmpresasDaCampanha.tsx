import { useCallback, useEffect, useState } from "react";

import { api } from "../api/cliente";
import type { components } from "../api/schema";
import { useEu } from "../eu";

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
  const [aviso, setAviso] = useState<string | null>(null);
  const { eu } = useEu();
  const ehVendedor = eu?.papel === "vendedor";

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

  async function assumir(id: string) {
    setAviso(null);
    const { data, response } = await api.POST("/empresas-da-campanha/{empresa_id}/assumir", {
      params: { path: { empresa_id: id } },
    });
    if (data) setAberta(data);
    else {
      setAberta(null);
      setAviso(
        response.status === 409 || response.status === 404
          ? "Outro vendedor assumiu esta empresa primeiro."
          : "Não foi possível assumir a empresa.",
      );
    }
    carregar();
  }

  async function abrir(id: string) {
    const { data } = await api.GET("/empresas-da-campanha/{empresa_id}", {
      params: { path: { empresa_id: id } },
    });
    if (data) setAberta(data);
  }

  function tabela(lista: Empresa[], vazia: string) {
    if (lista.length === 0) return <p className="suave">{vazia}</p>;
    return (
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
          {lista.map((e) => (
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
    );
  }

  return (
    <section className="painel">
      <h2>{ehVendedor ? "Empresas da campanha" : "Empresas na operação"}</h2>
      {aviso && <p className="erro">{aviso}</p>}
      {ehVendedor ? (
        <>
          <h3>Minhas empresas</h3>
          {tabela(empresas.filter((e) => e.responsavel?.id === eu?.usuario_id), "Você ainda não assumiu nenhuma empresa.")}
          <h3>Disponíveis</h3>
          {tabela(empresas.filter((e) => !e.responsavel), "Nenhuma empresa disponível.")}
        </>
      ) : (
        tabela(empresas, "Nenhuma empresa enviada para os vendedores ainda.")
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
            {ehVendedor && !aberta.responsavel && (
              <button onClick={() => assumir(aberta.id)}>Assumir esta empresa</button>
            )}
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
