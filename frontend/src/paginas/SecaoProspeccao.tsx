import { useCallback, useEffect, useState } from "react";

import { api } from "../api/cliente";
import type { components } from "../api/schema";
import { useEu } from "../eu";

type Execucao = components["schemas"]["ExecucaoOut"];
type PaginaDeCandidatos = components["schemas"]["PaginaDeCandidatos"];
type CandidatoDetalhe = components["schemas"]["CandidatoDetalhe"];

const NOMES_DOS_STATUS_DA_EXECUCAO: Record<string, string> = {
  na_fila: "Na fila",
  executando: "Executando",
  concluida: "Concluída",
  parcial: "Parcial",
  falhou: "Falhou",
};

const MOTIVOS_DE_PARADA: Record<string, string> = {
  limite_de_empresas: "limite de empresas atingido",
  teto_de_gasto: "teto de gasto atingido",
};

const EM_ANDAMENTO = new Set(["na_fila", "executando"]);

const NOMES_DOS_TIPOS: Record<string, string> = {
  prospeccao: "Prospecção",
  qualificacao: "Qualificação",
};

export const MOTIVOS_DE_RECUSA: Record<string, string> = {
  fora_do_perfil: "Fora do perfil",
  cnpj_inativo: "CNPJ inativo",
  fora_da_regiao: "Fora da região",
  dados_incompletos: "Dados incompletos",
  ja_e_cliente: "Já é cliente",
  duplicado: "Duplicado",
  opt_out: "Pediu para não ser contatado",
};

const NOMES_DOS_STATUS_DO_CANDIDATO: Record<string, string> = {
  coletado: "Aguardando qualificação",
  pendente: "Pendente",
  aprovado: "Aprovado",
  recusado: "Recusado",
};

export function SecaoProspeccao({ campanhaId }: { campanhaId: string }) {
  const { eu } = useEu();
  const [execucoes, setExecucoes] = useState<Execucao[]>([]);
  const [candidatos, setCandidatos] = useState<PaginaDeCandidatos | null>(null);
  const [aberto, setAberto] = useState<CandidatoDetalhe | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const caminho = { params: { path: { campanha_id: campanhaId } } };

  const carregar = useCallback(async () => {
    const [ex, ca] = await Promise.all([
      api.GET("/campanhas/{campanha_id}/execucoes", caminho),
      api.GET("/campanhas/{campanha_id}/candidatos", {
        params: { path: { campanha_id: campanhaId }, query: { limite: 200 } },
      }),
    ]);
    if (ex.data) setExecucoes(ex.data);
    if (ca.data) setCandidatos(ca.data);
  }, [campanhaId]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const ultimas = ["prospeccao", "qualificacao"]
    .map((tipo) => execucoes.find((e) => e.tipo === tipo))
    .filter((e): e is Execucao => !!e);
  const andamento = ultimas.some((e) => EM_ANDAMENTO.has(e.status));

  // Enquanto a execução anda, consulta o progresso a cada 2 segundos.
  useEffect(() => {
    if (!andamento) return;
    const id = window.setInterval(carregar, 2000);
    return () => window.clearInterval(id);
  }, [andamento, carregar]);

  async function executar() {
    setErro(null);
    const { error, response } = await api.POST("/campanhas/{campanha_id}/execucoes", caminho);
    if (error) {
      setErro(response.status === 409 ? "Já existe uma execução em andamento." : "Não foi possível iniciar.");
      return;
    }
    carregar();
  }

  async function abrir(candidatoId: string) {
    const { data } = await api.GET("/candidatos/{candidato_id}", {
      params: { path: { candidato_id: candidatoId } },
    });
    if (data) setAberto(data);
  }

  return (
    <section className="painel">
      <header className="cabecalho-da-pagina">
        <h2>Prospecção</h2>
        {eu?.papel === "coordenador" && (
          <button onClick={executar} disabled={!!andamento}>
            {andamento ? "Executando..." : "Executar prospecção"}
          </button>
        )}
      </header>
      {erro && <p className="erro">{erro}</p>}

      {ultimas.length === 0 && <p className="suave">Nenhuma execução ainda.</p>}
      {ultimas.map((e) => (
        <p key={e.id} className="suave">
          {NOMES_DOS_TIPOS[e.tipo] ?? e.tipo}: <strong>{NOMES_DOS_STATUS_DA_EXECUCAO[e.status]}</strong>
          {e.motivo_parada && ` (${MOTIVOS_DE_PARADA[e.motivo_parada] ?? e.motivo_parada})`}
          {" · "}
          {e.tipo === "prospeccao"
            ? `${e.gravadas} novas, ${e.duplicadas} já conhecidas`
            : `${e.gravadas} qualificadas, ${e.duplicadas} recusadas por regra`}
          {" · "}US$ {Number(e.custo_usd).toFixed(2)}
          {e.erro && <span className="erro"> · {e.erro}</span>}
        </p>
      ))}

      {candidatos && candidatos.total > 0 && (
        <table>
          <thead>
            <tr>
              <th>Empresa</th>
              <th>Segmento</th>
              <th>Tier</th>
              <th className="numero">Nota</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {candidatos.itens.map((c) => (
              <tr key={c.id} className="clicavel" onClick={() => abrir(c.id)}>
                <td>{c.empresa.nome_fantasia ?? c.empresa.razao_social}</td>
                <td>{c.empresa.segmento}</td>
                <td>
                  {c.tier_final ?? c.tier_sugerido ?? "—"}
                  {c.baixa_confianca && <span className="etiqueta alerta">baixa confiança</span>}
                  {c.em_revisao && <span className="etiqueta alerta">revisão</span>}
                </td>
                <td className="numero">{c.nota_total ?? "—"}</td>
                <td>
                  {NOMES_DOS_STATUS_DO_CANDIDATO[c.status]}
                  {c.motivo_recusa && ` · ${MOTIVOS_DE_RECUSA[c.motivo_recusa] ?? c.motivo_recusa}`}
                  {c.recusa_sugerida && <span className="suave"> (sugerido)</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {aberto && <GavetaDoCandidato candidato={aberto} aoFechar={() => setAberto(null)} />}
    </section>
  );
}

function GavetaDoCandidato({
  candidato,
  aoFechar,
}: {
  candidato: CandidatoDetalhe;
  aoFechar: () => void;
}) {
  const e = candidato.empresa;
  return (
    <div className="fundo-da-gaveta" onClick={aoFechar}>
      <aside className="gaveta" onClick={(ev) => ev.stopPropagation()}>
        <header className="cabecalho-da-pagina">
          <h2>{e.nome_fantasia ?? e.razao_social}</h2>
          <button className="link" onClick={aoFechar}>
            Fechar
          </button>
        </header>
        <dl>
          <dt>Razão social</dt>
          <dd>{e.razao_social}</dd>
          <dt>CNPJ</dt>
          <dd>{e.cnpj}</dd>
          <dt>Situação</dt>
          <dd>{e.situacao_cadastral ?? "—"}</dd>
          <dt>Segmento</dt>
          <dd>{e.segmento ?? "—"}</dd>
          <dt>Endereço</dt>
          <dd>{candidato.endereco ?? "—"}</dd>
          <dt>Site</dt>
          <dd>{e.site ? <a href={e.site}>{e.site}</a> : "—"}</dd>
        </dl>

        <h3>Notas</h3>
        {candidato.em_revisao && <p className="erro">Em revisão: {candidato.motivo_revisao}</p>}
        <dl>
          <dt>Total</dt>
          <dd>
            {candidato.nota_total ?? "—"} · tier {candidato.tier_final ?? candidato.tier_sugerido ?? "—"}
            {candidato.baixa_confianca && " · baixa confiança"}
          </dd>
          <dt>Aderência</dt>
          <dd>
            {candidato.nota_aderencia ?? "—"}
            {typeof candidato.justificativas.aderencia === "string" && (
              <span className="suave"> · {candidato.justificativas.aderencia}</span>
            )}
          </dd>
          <dt>Potencial</dt>
          <dd>
            {candidato.nota_potencial ?? "—"}
            {typeof candidato.justificativas.potencial === "string" && (
              <span className="suave"> · {candidato.justificativas.potencial}</span>
            )}
          </dd>
          <dt>Geografia</dt>
          <dd>{candidato.nota_geografia ?? "—"}</dd>
          <dt>Dados</dt>
          <dd>{candidato.nota_dados ?? "—"}</dd>
          {candidato.lacunas.length > 0 && (
            <>
              <dt>Lacunas</dt>
              <dd>{candidato.lacunas.join("; ")}</dd>
            </>
          )}
        </dl>

        <h3>Contatos</h3>
        {candidato.contatos.length === 0 && <p className="suave">Nenhum contato.</p>}
        <ul>
          {candidato.contatos.map((c) => (
            <li key={`${c.tipo}-${c.valor}`}>
              {c.valor}{" "}
              <span className="suave">
                ({c.tipo}
                {c.nome ? `, ${c.nome}` : ""} · {c.fonte}
                {c.status_validacao ? ` · ${c.status_validacao}` : ""})
              </span>
            </li>
          ))}
        </ul>

        {Object.keys(candidato.sinais).length > 0 && (
          <>
            <h3>Sinais comerciais</h3>
            <pre className="sinais">{JSON.stringify(candidato.sinais, null, 2)}</pre>
          </>
        )}

        <h3>Evidências</h3>
        <table>
          <thead>
            <tr>
              <th>Campo</th>
              <th>Valor</th>
              <th>Fonte</th>
              <th>Data</th>
            </tr>
          </thead>
          <tbody>
            {candidato.evidencias.map((ev, i) => (
              <tr key={i}>
                <td>{ev.campo}</td>
                <td>{ev.valor}</td>
                <td>{ev.url ? <a href={ev.url}>{ev.fonte}</a> : ev.fonte}</td>
                <td>{new Date(ev.coletado_em).toLocaleDateString("pt-BR")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </aside>
    </div>
  );
}
