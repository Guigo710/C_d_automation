import { useState } from "react";

import { api } from "../api/cliente";
import type { components } from "../api/schema";
import {
  BarraDeNota,
  Gaveta,
  MOTIVOS_DE_RECUSA,
  NOMES_DAS_FONTES,
  Tier,
  formatarCnpj,
} from "../ui";

type CandidatoDetalhe = components["schemas"]["CandidatoDetalhe"];
type Motivo = components["schemas"]["RecusaIn"]["motivo"];
type TierLetra = "A" | "B" | "C";

const DIMENSOES: { chave: "aderencia" | "potencial" | "geografia" | "dados"; nome: string; peso: string }[] = [
  { chave: "aderencia", nome: "Aderência ao perfil", peso: "40%" },
  { chave: "potencial", nome: "Potencial de compra", peso: "25%" },
  { chave: "geografia", nome: "Geografia", peso: "20%" },
  { chave: "dados", nome: "Qualidade dos dados", peso: "15%" },
];

export function GavetaDoCandidato({
  candidato,
  cidade,
  podeDecidir,
  aoFechar,
  aoMudar,
}: {
  candidato: CandidatoDetalhe;
  cidade: string;
  podeDecidir: boolean;
  aoFechar: () => void;
  aoMudar: () => Promise<void>;
}) {
  const e = candidato.empresa;
  const [motivo, setMotivo] = useState<Motivo>("fora_do_perfil");
  const [novoTier, setNovoTier] = useState<TierLetra>("A");
  const [justificativa, setJustificativa] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const caminho = { params: { path: { candidato_id: candidato.id } } };
  const tier = candidato.tier_final ?? candidato.tier_sugerido;

  async function agir(acao: () => Promise<{ error?: unknown }>) {
    setErro(null);
    const { error } = await acao();
    if (error) setErro("Não foi possível concluir a ação.");
    else await aoMudar();
  }

  const notas: Record<string, number | null | undefined> = {
    aderencia: candidato.nota_aderencia,
    potencial: candidato.nota_potencial,
    geografia: candidato.nota_geografia,
    dados: candidato.nota_dados,
  };
  const justificativas = candidato.justificativas as Record<string, unknown>;

  return (
    <Gaveta
      titulo={e.nome_fantasia ?? e.razao_social}
      subtitulo={`${cidade} · ${e.segmento ?? "segmento não informado"}`}
      aoFechar={aoFechar}
    >
      <div className="linha" style={{ alignItems: "center" }}>
        <Tier tier={tier} />
        <div style={{ flex: 1 }}>
          <BarraDeNota nota={candidato.nota_total} />
        </div>
        {candidato.baixa_confianca && <span className="etiqueta alerta">baixa confiança</span>}
        {candidato.em_revisao && <span className="etiqueta perigo">em revisão</span>}
        {candidato.status === "aprovado" && <span className="etiqueta sucesso">aprovado</span>}
        {candidato.motivo_recusa && (
          <span className="etiqueta perigo">
            {MOTIVOS_DE_RECUSA[candidato.motivo_recusa]}
            {candidato.recusa_sugerida ? " · sugerido" : ""}
          </span>
        )}
      </div>
      {candidato.em_revisao && <p className="erro">Em revisão: {candidato.motivo_revisao}</p>}

      {podeDecidir && (
        <section className="acoes">
          {candidato.status === "pendente" && (
            <button
              onClick={() =>
                agir(() =>
                  api.POST("/campanhas/{campanha_id}/aprovacoes", {
                    params: { path: { campanha_id: candidato.campanha_id } },
                    body: { candidato_ids: [candidato.id] },
                  }),
                )
              }
            >
              Aprovar
            </button>
          )}
          {candidato.status !== "aprovado" && (
            <div className="linha">
              <select value={motivo} onChange={(ev) => setMotivo(ev.target.value as Motivo)}>
                {Object.entries(MOTIVOS_DE_RECUSA).map(([valor, nome]) => (
                  <option key={valor} value={valor}>
                    {nome}
                  </option>
                ))}
              </select>
              <button
                className="secundario"
                onClick={() => agir(() => api.POST("/candidatos/{candidato_id}/recusa", { ...caminho, body: { motivo } }))}
              >
                Recusar
              </button>
            </div>
          )}
          {candidato.status === "recusado" && candidato.recusa_sugerida && (
            <button
              className="secundario"
              onClick={() => agir(() => api.POST("/candidatos/{candidato_id}/restauracao", caminho))}
            >
              Restaurar recusa sugerida
            </button>
          )}
          {(candidato.status === "pendente" || candidato.status === "aprovado") && (
            <div className="linha">
              <select value={novoTier} onChange={(ev) => setNovoTier(ev.target.value as TierLetra)}>
                <option value="A">Tier A</option>
                <option value="B">Tier B</option>
                <option value="C">Tier C</option>
              </select>
              <input
                placeholder="Justificativa da troca de tier"
                value={justificativa}
                onChange={(ev) => setJustificativa(ev.target.value)}
              />
              <button
                className="secundario"
                disabled={justificativa.trim().length < 3}
                onClick={() =>
                  agir(() =>
                    api.PUT("/candidatos/{candidato_id}/tier", {
                      ...caminho,
                      body: { tier: novoTier, justificativa },
                    }),
                  )
                }
              >
                Mudar tier
              </button>
            </div>
          )}
          {erro && <p className="erro">{erro}</p>}
        </section>
      )}

      <section>
        <h3>Notas por dimensão</h3>
        <div className="dimensoes">
          {DIMENSOES.map((d) => (
            <div key={d.chave} className="dimensao">
              <div className="cabeca">
                <span>{d.nome}</span>
                <span className="suave mono">peso {d.peso}</span>
              </div>
              <BarraDeNota nota={notas[d.chave]} />
              {typeof justificativas[d.chave] === "string" && <p>{justificativas[d.chave] as string}</p>}
            </div>
          ))}
        </div>
        {candidato.lacunas.length > 0 && (
          <p className="suave" style={{ marginTop: 12 }}>
            <strong>Lacunas:</strong> {candidato.lacunas.join("; ")}
          </p>
        )}
      </section>

      <section>
        <h3>Empresa</h3>
        <dl>
          <dt>Razão social</dt>
          <dd>{e.razao_social}</dd>
          <dt>CNPJ</dt>
          <dd className="mono">{formatarCnpj(e.cnpj)}</dd>
          <dt>Situação</dt>
          <dd>{e.situacao_cadastral ?? "–"}</dd>
          <dt>Endereço</dt>
          <dd>{candidato.endereco ?? "–"}</dd>
          <dt>Site</dt>
          <dd>{e.site ? <a href={e.site}>{e.site}</a> : "–"}</dd>
        </dl>
      </section>

      <section>
        <h3>Contatos</h3>
        {candidato.contatos.length === 0 && <p className="suave">Nenhum contato.</p>}
        <ul>
          {candidato.contatos.map((c) => (
            <li key={`${c.tipo}-${c.valor}`}>
              <span className="mono">{c.valor}</span>{" "}
              <span className="suave">
                {c.tipo}
                {c.nome ? ` · ${c.nome}` : ""} · {NOMES_DAS_FONTES[c.fonte] ?? c.fonte}
                {c.status_validacao ? ` · ${c.status_validacao}` : ""}
              </span>
            </li>
          ))}
        </ul>
      </section>

      {Object.keys(candidato.sinais).length > 0 && (
        <section>
          <h3>Sinais comerciais</h3>
          <pre className="sinais">{JSON.stringify(candidato.sinais, null, 2)}</pre>
        </section>
      )}

      <section>
        <h3>Evidências</h3>
        <div className="tabela-rolavel">
          <table>
            <thead>
              <tr>
                <th>Campo</th>
                <th>Valor</th>
                <th>Fonte</th>
                <th>Coleta</th>
              </tr>
            </thead>
            <tbody>
              {candidato.evidencias.map((ev, i) => (
                <tr key={i}>
                  <td>{ev.campo}</td>
                  <td>{ev.valor}</td>
                  <td>{ev.url ? <a href={ev.url}>{NOMES_DAS_FONTES[ev.fonte] ?? ev.fonte}</a> : (NOMES_DAS_FONTES[ev.fonte] ?? ev.fonte)}</td>
                  <td className="mono">{new Date(ev.coletado_em).toLocaleDateString("pt-BR")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </Gaveta>
  );
}
