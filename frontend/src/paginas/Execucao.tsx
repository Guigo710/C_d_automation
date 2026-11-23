import { useCallback, useEffect, useState } from "react";

import { api } from "../api/cliente";
import type { components } from "../api/schema";
import { useEu } from "../eu";
import { formatarDolar } from "../ui";

type Execucao = components["schemas"]["ExecucaoOut"];
type Campanha = components["schemas"]["CampanhaOut"];

const STATUS: Record<string, { nome: string; classe: string }> = {
  na_fila: { nome: "Na fila", classe: "alerta" },
  executando: { nome: "Executando", classe: "alerta" },
  concluida: { nome: "Concluída", classe: "sucesso" },
  parcial: { nome: "Parcial", classe: "alerta" },
  falhou: { nome: "Falhou", classe: "perigo" },
};

const MOTIVOS: Record<string, string> = {
  limite_de_empresas: "limite de empresas atingido",
  teto_de_gasto: "teto de gasto atingido",
  sem_chave_ia: "falta a chave da Claude API",
  organizacao_sem_configuracao: "organização sem regras configuradas",
};

const ETAPAS: { tipo: string; agente: string; nome: string; descricao: string; rotulos: [string, string, string] }[] = [
  {
    tipo: "prospeccao",
    agente: "Agente 1",
    nome: "Prospecção",
    descricao: "Encontra empresas por CNPJ, Maps e site",
    rotulos: ["encontradas", "novas", "já conhecidas"],
  },
  {
    tipo: "qualificacao",
    agente: "Agente 2",
    nome: "Qualificação",
    descricao: "Exclusões, notas e tier A, B ou C",
    rotulos: ["processadas", "qualificadas", "recusadas por regra"],
  },
  {
    tipo: "ficha",
    agente: "Agente 3",
    nome: "Fichas de abordagem",
    descricao: "Resumo para o vendedor ler antes do contato",
    rotulos: ["processadas", "fichas prontas", "—"],
  },
];

const EM_ANDAMENTO = new Set(["na_fila", "executando"]);

export function Execucao({ campanhaId }: { campanhaId: string }) {
  const { eu } = useEu();
  const podeExecutar = eu?.papel === "coordenador";
  const [execucoes, setExecucoes] = useState<Execucao[]>([]);
  const [campanha, setCampanha] = useState<Campanha | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const caminho = { params: { path: { campanha_id: campanhaId } } };

  const carregar = useCallback(async () => {
    const [ex, cp] = await Promise.all([
      api.GET("/campanhas/{campanha_id}/execucoes", { params: { path: { campanha_id: campanhaId } } }),
      api.GET("/campanhas/{campanha_id}", { params: { path: { campanha_id: campanhaId } } }),
    ]);
    if (ex.data) setExecucoes(ex.data);
    if (cp.data) setCampanha(cp.data);
  }, [campanhaId]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const andamento = execucoes.some((e) => EM_ANDAMENTO.has(e.status));
  useEffect(() => {
    if (!andamento) return;
    const id = window.setInterval(carregar, 1500);
    return () => window.clearInterval(id);
  }, [andamento, carregar]);

  async function executar() {
    setErro(null);
    const { error, response } = await api.POST("/campanhas/{campanha_id}/execucoes", caminho);
    if (error) setErro(response.status === 409 ? "Já existe uma execução em andamento." : "Não foi possível iniciar.");
    await carregar();
  }

  async function requalificar() {
    setErro(null);
    const { error } = await api.POST("/campanhas/{campanha_id}/qualificacoes", caminho);
    if (error) setErro("Não foi possível pôr a qualificação na fila.");
    await carregar();
  }

  const gasto = execucoes.reduce((soma, e) => soma + Number(e.custo_usd), 0);
  const teto = Number(campanha?.teto_gasto_usd ?? 0);

  return (
    <>
      <header className="cabecalho">
        <div>
          <p className="rotulo">Agentes da campanha</p>
          <h1>Execução</h1>
        </div>
        {podeExecutar && (
          <div className="acoes-do-topo">
            <button className="secundario" onClick={requalificar} disabled={andamento}>
              Qualificar pendentes
            </button>
            <button onClick={executar} disabled={andamento}>
              {andamento ? "Executando..." : "Executar prospecção"}
            </button>
          </div>
        )}
      </header>
      {erro && <p className="erro">{erro}</p>}

      <div className="etapas">
        {ETAPAS.map((etapa) => {
          const ultima = execucoes.find((e) => e.tipo === etapa.tipo);
          const status = ultima ? STATUS[ultima.status] : null;
          return (
            <section
              key={etapa.tipo}
              className={`etapa${ultima && EM_ANDAMENTO.has(ultima.status) ? " executando" : ""}${ultima?.status === "falhou" ? " falhou" : ""}`}
            >
              <header>
                <div>
                  <p className="rotulo">{etapa.agente}</p>
                  <h3>{etapa.nome}</h3>
                </div>
                {status ? (
                  <span className={`etiqueta ${status.classe}`}>{status.nome}</span>
                ) : (
                  <span className="etiqueta">Não executado</span>
                )}
              </header>
              <p className="suave" style={{ margin: "6px 0 0", fontSize: "0.85rem" }}>
                {etapa.descricao}
              </p>
              <div className="contagens">
                {[ultima?.encontradas, ultima?.gravadas, etapa.tipo === "ficha" ? undefined : ultima?.duplicadas].map(
                  (n, i) => (
                    <div key={i}>
                      <span>{etapa.rotulos[i] === "—" ? "" : (n ?? 0)}</span>
                      <small>{etapa.rotulos[i] === "—" ? "" : etapa.rotulos[i]}</small>
                    </div>
                  ),
                )}
              </div>
              <p className="mono suave" style={{ margin: 0, fontSize: "0.8rem" }}>
                custo {formatarDolar(ultima?.custo_usd ?? 0)}
                {ultima?.terminado_em && ` · ${new Date(ultima.terminado_em).toLocaleString("pt-BR")}`}
              </p>
              {ultima?.motivo_parada && (
                <p className="suave" style={{ margin: "6px 0 0", fontSize: "0.85rem" }}>
                  Parou: {MOTIVOS[ultima.motivo_parada] ?? ultima.motivo_parada}
                </p>
              )}
              {ultima?.erro && <p className="erro" style={{ fontSize: "0.85rem", marginTop: 6 }}>{ultima.erro}</p>}
            </section>
          );
        })}
      </div>

      <section className="painel gasto">
        <h2>Gasto da campanha</h2>
        <div className="trilho">
          <div className="preenchido" style={{ width: `${teto > 0 ? Math.min(100, (gasto / teto) * 100) : 0}%` }} />
        </div>
        <p className="mono suave" style={{ margin: 0 }}>
          {formatarDolar(gasto)} de {formatarDolar(teto)} · os agentes param ao atingir o teto
        </p>
      </section>

      <section className="painel">
        <h2>Histórico de execuções</h2>
        {execucoes.length === 0 ? (
          <p className="suave">Nenhuma execução ainda.</p>
        ) : (
          <div className="tabela-rolavel">
            <table>
              <thead>
                <tr>
                  <th>Etapa</th>
                  <th>Status</th>
                  <th className="numero">Processadas</th>
                  <th className="numero">Gravadas</th>
                  <th className="numero">Custo</th>
                  <th>Início</th>
                </tr>
              </thead>
              <tbody>
                {execucoes.map((e) => (
                  <tr key={e.id}>
                    <td>{ETAPAS.find((x) => x.tipo === e.tipo)?.nome ?? e.tipo}</td>
                    <td>
                      <span className={`etiqueta ${STATUS[e.status]?.classe ?? ""}`}>{STATUS[e.status]?.nome}</span>
                    </td>
                    <td className="numero">{e.encontradas}</td>
                    <td className="numero">{e.gravadas}</td>
                    <td className="numero">{formatarDolar(e.custo_usd)}</td>
                    <td className="mono suave">{new Date(e.criado_em).toLocaleString("pt-BR")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
