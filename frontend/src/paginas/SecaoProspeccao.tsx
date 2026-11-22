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

  const ultima = execucoes[0];
  const andamento = ultima && EM_ANDAMENTO.has(ultima.status);

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

      {ultima ? (
        <p className="suave">
          Última execução: <strong>{NOMES_DOS_STATUS_DA_EXECUCAO[ultima.status]}</strong>
          {ultima.motivo_parada && ` (${MOTIVOS_DE_PARADA[ultima.motivo_parada] ?? ultima.motivo_parada})`}
          {" · "}
          {ultima.gravadas} novas, {ultima.duplicadas} já conhecidas · US$ {Number(ultima.custo_usd).toFixed(2)}
          {ultima.erro && <span className="erro"> · {ultima.erro}</span>}
        </p>
      ) : (
        <p className="suave">Nenhuma execução ainda.</p>
      )}

      {candidatos && candidatos.total > 0 && (
        <table>
          <thead>
            <tr>
              <th>Empresa</th>
              <th>Segmento</th>
              <th>CNPJ</th>
              <th>Situação</th>
            </tr>
          </thead>
          <tbody>
            {candidatos.itens.map((c) => (
              <tr key={c.id} className="clicavel" onClick={() => abrir(c.id)}>
                <td>{c.empresa.nome_fantasia ?? c.empresa.razao_social}</td>
                <td>{c.empresa.segmento}</td>
                <td>{c.empresa.cnpj}</td>
                <td>{c.empresa.situacao_cadastral}</td>
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

        <h3>Contatos</h3>
        {candidato.contatos.length === 0 && <p className="suave">Nenhum contato.</p>}
        <ul>
          {candidato.contatos.map((c) => (
            <li key={`${c.tipo}-${c.valor}`}>
              {c.valor} <span className="suave">({c.tipo}{c.nome ? `, ${c.nome}` : ""} · {c.fonte})</span>
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
