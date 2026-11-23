import { useCallback, useEffect, useState } from "react";

import { api } from "../api/cliente";
import type { components } from "../api/schema";
import { useEu } from "../eu";
import { EmpresasDaCampanha } from "./EmpresasDaCampanha";
import { Kanban } from "./Kanban";

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


export function SecaoProspeccao({ campanhaId }: { campanhaId: string }) {
  const { eu } = useEu();
  const [execucoes, setExecucoes] = useState<Execucao[]>([]);
  const [candidatos, setCandidatos] = useState<PaginaDeCandidatos | null>(null);
  const [aberto, setAberto] = useState<CandidatoDetalhe | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [versaoDaOperacao, setVersaoDaOperacao] = useState(0);
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

  const podeDecidir = eu?.papel === "coordenador";

  async function aprovar(ids: string[]) {
    if (ids.length === 0) return;
    const { error } = await api.POST("/campanhas/{campanha_id}/aprovacoes", {
      ...caminho,
      body: { candidato_ids: ids },
    });
    if (error) setErro("Não foi possível aprovar.");
    await carregar();
  }

  const aprovados = candidatos?.itens.filter((c) => c.status === "aprovado") ?? [];

  async function subirParaOperacao() {
    setErro(null);
    const { data, error } = await api.POST("/campanhas/{campanha_id}/promocoes", {
      params: {
        path: { campanha_id: campanhaId },
        // Uma chave nova por clique: repetir o mesmo pedido não duplica nada.
        header: { "Idempotency-Key": crypto.randomUUID() },
      },
      body: { candidato_ids: aprovados.map((c) => c.id) },
    });
    if (error) setErro("Não foi possível enviar para a operação.");
    else if (data) setVersaoDaOperacao((v) => v + 1);
  }

  async function exportar() {
    setErro(null);
    const { data, error } = await api.GET("/campanhas/{campanha_id}/aprovados.xlsx", {
      ...caminho,
      parseAs: "blob",
    });
    if (error || !data) {
      setErro("Não foi possível exportar.");
      return;
    }
    const url = URL.createObjectURL(data as Blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "aprovados.xlsx";
    link.click();
    URL.revokeObjectURL(url);
  }

  async function abrir(candidatoId: string) {
    const { data } = await api.GET("/candidatos/{candidato_id}", {
      params: { path: { candidato_id: candidatoId } },
    });
    if (data) setAberto(data);
  }

  return (
    <>
    <section className="painel">
      <header className="cabecalho-da-pagina">
        <h2>Prospecção</h2>
        {eu?.papel === "coordenador" && (
          <div className="linha">
            <button onClick={executar} disabled={!!andamento}>
              {andamento ? "Executando..." : "Executar prospecção"}
            </button>
            <button className="secundario" onClick={subirParaOperacao} disabled={aprovados.length === 0}>
              Subir {aprovados.length} aprovado(s) para operação
            </button>
            <button className="secundario" onClick={exportar} disabled={aprovados.length === 0}>
              Exportar aprovados (Excel)
            </button>
          </div>
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
        <Kanban
          candidatos={candidatos.itens}
          podeDecidir={podeDecidir}
          aoAbrir={abrir}
          aoAprovar={aprovar}
        />
      )}

      {aberto && (
        <GavetaDoCandidato
          candidato={aberto}
          podeDecidir={podeDecidir}
          aoFechar={() => setAberto(null)}
          aoMudar={async () => {
            await carregar();
            await abrir(aberto.id);
          }}
        />
      )}
    </section>
    <EmpresasDaCampanha campanhaId={campanhaId} versao={versaoDaOperacao} />
    </>
  );
}

type Motivo = components["schemas"]["RecusaIn"]["motivo"];

function GavetaDoCandidato({
  candidato,
  podeDecidir,
  aoFechar,
  aoMudar,
}: {
  candidato: CandidatoDetalhe;
  podeDecidir: boolean;
  aoFechar: () => void;
  aoMudar: () => Promise<void>;
}) {
  const e = candidato.empresa;
  const [motivo, setMotivo] = useState<Motivo>("fora_do_perfil");
  const [novoTier, setNovoTier] = useState<"A" | "B" | "C">("A");
  const [justificativa, setJustificativa] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const caminho = { params: { path: { candidato_id: candidato.id } } };

  async function agir(acao: () => Promise<{ error?: unknown }>) {
    setErro(null);
    const { error } = await acao();
    if (error) setErro("Não foi possível concluir a ação.");
    else await aoMudar();
  }

  const acoes = podeDecidir && (
    <div className="acoes">
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
        <button className="secundario" onClick={() => agir(() => api.POST("/candidatos/{candidato_id}/restauracao", caminho))}>
          Restaurar (recusa sugerida)
        </button>
      )}
      {(candidato.status === "pendente" || candidato.status === "aprovado") && (
        <div className="linha">
          <select value={novoTier} onChange={(ev) => setNovoTier(ev.target.value as "A" | "B" | "C")}>
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
                api.PUT("/candidatos/{candidato_id}/tier", { ...caminho, body: { tier: novoTier, justificativa } }),
              )
            }
          >
            Trocar tier
          </button>
        </div>
      )}
      {erro && <p className="erro">{erro}</p>}
    </div>
  );
  return (
    <div className="fundo-da-gaveta" onClick={aoFechar}>
      <aside className="gaveta" onClick={(ev) => ev.stopPropagation()}>
        <header className="cabecalho-da-pagina">
          <h2>{e.nome_fantasia ?? e.razao_social}</h2>
          <button className="link" onClick={aoFechar}>
            Fechar
          </button>
        </header>
        {acoes}
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
