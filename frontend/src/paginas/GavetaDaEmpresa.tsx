import { useEffect, useState } from "react";

import { api } from "../api/cliente";
import type { components } from "../api/schema";
import { useEu } from "../eu";
import { BarraDeNota, Gaveta, Tier, formatarCnpj } from "../ui";

type Detalhe = components["schemas"]["EmpresaDaCampanhaDetalhe"];

const EVENTOS: Record<string, string> = {
  aprovada: "Aprovada na triagem",
  promovida: "Enviada para a operação",
  assumida: "Assumida pelo vendedor",
  atribuida: "Atribuída pelo coordenador",
  transferida: "Transferida pelo coordenador",
};

const STATUS_DA_FICHA: Record<string, string> = {
  preparando: "Ficha em preparo",
  pronta: "Ficha pronta",
  falhou: "Ficha não gerada",
};

export function GavetaDaEmpresa({
  empresaId,
  cidade,
  aoFechar,
  aoMudar,
}: {
  empresaId: string;
  cidade: (codigo: string | null | undefined) => string;
  aoFechar: () => void;
  aoMudar: () => void;
}) {
  const { eu } = useEu();
  const [empresa, setEmpresa] = useState<Detalhe | null>(null);
  const [membros, setMembros] = useState<{ id: string; nome: string }[]>([]);
  const [destino, setDestino] = useState("");
  const [aviso, setAviso] = useState<string | null>(null);
  const [perdida, setPerdida] = useState(false);
  const ehVendedor = eu?.papel === "vendedor";
  const ehCoordenador = eu?.papel === "coordenador";
  const caminho = { params: { path: { empresa_id: empresaId } } };

  useEffect(() => {
    api.GET("/empresas-da-campanha/{empresa_id}", caminho).then(({ data }) => setEmpresa(data ?? null));
  }, [empresaId]);

  useEffect(() => {
    if (!ehCoordenador || !empresa) return;
    api
      .GET("/campanhas/{campanha_id}", { params: { path: { campanha_id: empresa.campanha_id } } })
      .then(({ data }) => data && setMembros(data.membros));
  }, [ehCoordenador, empresa]);

  async function assumir() {
    setAviso(null);
    const { data, response } = await api.POST("/empresas-da-campanha/{empresa_id}/assumir", caminho);
    if (data) setEmpresa(data);
    else if (response.status === 409 || response.status === 404) {
      setPerdida(true);
      setAviso("Outro vendedor assumiu esta empresa primeiro. Ela saiu da sua lista.");
    } else setAviso("Não foi possível assumir a empresa.");
    aoMudar();
  }

  async function definirResponsavel() {
    if (!destino) return;
    const { data } = await api.PUT("/empresas-da-campanha/{empresa_id}/responsavel", {
      ...caminho,
      body: { vendedor_id: destino },
    });
    if (data) {
      setEmpresa(data);
      setDestino("");
      aoMudar();
    } else setAviso("Não foi possível trocar o responsável.");
  }

  if (!empresa) {
    return (
      <Gaveta titulo="Carregando..." aoFechar={aoFechar}>
        {aviso && <p className="erro">{aviso}</p>}
      </Gaveta>
    );
  }

  const e = empresa.empresa;
  return (
    <Gaveta
      titulo={e.nome_fantasia ?? e.razao_social}
      subtitulo={`${cidade(e.municipio_ibge)} · ${e.segmento ?? ""} · ${empresa.campanha_nome}`}
      aoFechar={aoFechar}
    >
      <div className="linha" style={{ alignItems: "center" }}>
        <Tier tier={empresa.tier} />
        <div style={{ flex: 1 }}>
          <BarraDeNota nota={empresa.nota_total} />
        </div>
        <span className="etiqueta">
          {perdida ? "com outro vendedor" : empresa.responsavel ? `com ${empresa.responsavel.nome}` : "sem responsável"}
        </span>
      </div>
      {aviso && <p className="erro">{aviso}</p>}

      {ehVendedor && !empresa.responsavel && !perdida && (
        <section>
          <button onClick={assumir}>Assumir esta empresa</button>
        </section>
      )}

      {ehCoordenador && (
        <section className="acoes">
          <span className="suave">Responsável: {empresa.responsavel?.nome ?? "ninguém ainda"}</span>
          <div className="linha">
            <select value={destino} onChange={(ev) => setDestino(ev.target.value)}>
              <option value="">Escolher vendedor da campanha</option>
              {membros
                .filter((m) => m.id !== empresa.responsavel?.id)
                .map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.nome}
                  </option>
                ))}
            </select>
            <button disabled={!destino} onClick={definirResponsavel}>
              {empresa.responsavel ? "Transferir" : "Atribuir"}
            </button>
          </div>
        </section>
      )}

      <section>
        <h3>Ficha de abordagem</h3>
        {empresa.ficha_status === "pronta" ? (
          <p className="ficha">{empresa.ficha}</p>
        ) : (
          <p className="suave">{STATUS_DA_FICHA[empresa.ficha_status]}</p>
        )}
      </section>

      <section>
        <h3>Contato</h3>
        {empresa.contato_oculto ? (
          <p className="oculto">O contato aparece depois que você assumir a empresa.</p>
        ) : empresa.contatos.length === 0 ? (
          <p className="suave">Nenhum contato.</p>
        ) : (
          <ul>
            {empresa.contatos.map((c) => (
              <li key={`${c.tipo}-${c.valor}`}>
                <span className="mono">{c.valor}</span>{" "}
                <span className="suave">
                  {c.tipo}
                  {c.nome ? ` · ${c.nome}` : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h3>Dados</h3>
        <dl>
          <dt>Razão social</dt>
          <dd>{e.razao_social}</dd>
          <dt>CNPJ</dt>
          <dd className="mono">{formatarCnpj(e.cnpj)}</dd>
          <dt>Endereço</dt>
          <dd>{empresa.endereco ?? "–"}</dd>
          <dt>Site</dt>
          <dd>{e.site ? <a href={e.site}>{e.site}</a> : "–"}</dd>
        </dl>
      </section>

      <section>
        <h3>Histórico</h3>
        {empresa.historico.length === 0 ? (
          <p className="suave">O histórico aparece para o responsável.</p>
        ) : (
          <ul>
            {empresa.historico.map((h, i) => (
              <li key={i}>
                {EVENTOS[h.tipo] ?? h.tipo}{" "}
                <span className="suave mono">{new Date(h.ocorrido_em).toLocaleString("pt-BR")}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </Gaveta>
  );
}

export { STATUS_DA_FICHA };
