import { useEffect, useState, type FormEvent } from "react";

import { api } from "../api/cliente";
import type { components } from "../api/schema";
import { Kpi, formatarDolar } from "../ui";

type Configuracao = components["schemas"]["ConfiguracaoDaOrganizacao"];
type Fornecedor = "anthropic" | "google_places" | "brave";

const FORNECEDORES: Record<string, { nome: string; uso: string }> = {
  anthropic: { nome: "Claude API (Anthropic)", uso: "Qualificação e fichas de abordagem" },
  google_places: { nome: "Google Places", uso: "Confirma lojas e acha site e telefone" },
  brave: { nome: "Brave Search", uso: "Acha o site quando a empresa não informa" },
};

export function Configuracao() {
  const [config, setConfig] = useState<Configuracao | null>(null);
  const [teto, setTeto] = useState("");
  const [novasChaves, setNovasChaves] = useState<Record<string, string>>({});
  const [remover, setRemover] = useState<Fornecedor | null>(null);
  const [mensagem, setMensagem] = useState<{ tipo: "erro" | "aviso"; texto: string } | null>(null);

  function aplicar(dados: Configuracao) {
    setConfig(dados);
    setTeto(dados.teto_mensal_usd);
  }

  useEffect(() => {
    api.GET("/configuracao").then(({ data }) => data && aplicar(data));
  }, []);

  async function salvarTeto(evento: FormEvent) {
    evento.preventDefault();
    const { data } = await api.PUT("/configuracao/teto", { body: { teto_mensal_usd: teto } });
    if (data) {
      aplicar(data);
      setMensagem({ tipo: "aviso", texto: "Teto salvo." });
    } else setMensagem({ tipo: "erro", texto: "Não foi possível salvar o teto." });
  }

  async function salvarChave(fornecedor: Fornecedor) {
    const chave = novasChaves[fornecedor]?.trim();
    if (!chave) return;
    const { data, response } = await api.PUT("/configuracao/chaves/{fornecedor}", {
      params: { path: { fornecedor } },
      body: { chave },
    });
    if (data) {
      aplicar(data);
      setNovasChaves({ ...novasChaves, [fornecedor]: "" });
      setMensagem({ tipo: "aviso", texto: `Chave do ${FORNECEDORES[fornecedor].nome} salva.` });
    } else if (response.status === 503) {
      setMensagem({ tipo: "erro", texto: "O servidor não tem a cifragem de chaves configurada." });
    } else setMensagem({ tipo: "erro", texto: "Não foi possível salvar a chave." });
  }

  async function confirmarRemocao() {
    if (!remover) return;
    const fornecedor = remover;
    setRemover(null);
    const { data } = await api.DELETE("/configuracao/chaves/{fornecedor}", {
      params: { path: { fornecedor } },
    });
    if (data) {
      aplicar(data);
      setMensagem({ tipo: "aviso", texto: `Chave do ${FORNECEDORES[fornecedor].nome} removida.` });
    } else setMensagem({ tipo: "erro", texto: "Não foi possível remover a chave." });
  }

  if (!config) return <p className="suave">Carregando...</p>;

  const gasto = Number(config.gasto_do_mes_usd);
  const limite = Number(config.teto_mensal_usd);
  const usado = limite > 0 ? Math.min(100, (gasto / limite) * 100) : 0;

  return (
    <>
      <header className="cabecalho">
        <div>
          <p className="rotulo">Administração</p>
          <h1>Configuração</h1>
        </div>
      </header>
      {mensagem && (
        <p className={mensagem.tipo} role="status" style={{ marginBottom: 16 }}>
          {mensagem.texto}
        </p>
      )}

      <div className="kpis">
        <Kpi rotulo="Gasto do mês" valor={formatarDolar(gasto)} destaque />
        <Kpi rotulo="Teto mensal" valor={formatarDolar(limite)} />
        <Kpi rotulo="Usado" valor={`${usado.toFixed(0)}%`} />
      </div>

      <section className="painel gasto">
        <h2>Teto de gasto mensal</h2>
        <p className="suave" style={{ margin: 0 }}>
          Soma de dados e IA de todas as campanhas no mês. Ao atingir o teto, os agentes param.
        </p>
        <div className="trilho">
          <div className="preenchido" style={{ width: `${usado}%` }} />
        </div>
        <form onSubmit={salvarTeto} className="formulario-em-linha">
          <label>
            Novo teto (US$)
            <input type="number" min={0} step="0.01" value={teto} onChange={(e) => setTeto(e.target.value)} />
          </label>
          <button type="submit">Salvar teto</button>
        </form>
      </section>

      <section className="painel">
        <h2>Chaves de API</h2>
        <p className="suave" style={{ marginTop: 0 }}>
          A organização paga os próprios fornecedores. As chaves ficam cifradas no servidor e nunca são
          mostradas de novo; aparece só o final.
        </p>
        <div className="lista-de-chaves">
          {config.chaves.map((c) => {
            const fornecedor = c.fornecedor as Fornecedor;
            const info = FORNECEDORES[c.fornecedor];
            return (
              <div key={c.fornecedor} className="chave">
                <div className="chave-info">
                  <strong>{info?.nome ?? c.fornecedor}</strong>
                  <span className="suave">{info?.uso}</span>
                  {c.configurada ? (
                    <span className="etiqueta sucesso">
                      configurada · final <span className="mono">{c.final}</span>
                    </span>
                  ) : (
                    <span className="etiqueta">não configurada</span>
                  )}
                </div>
                <div className="chave-acoes">
                  <input
                    type="password"
                    autoComplete="off"
                    aria-label={`Nova chave do ${info?.nome ?? c.fornecedor}`}
                    placeholder={c.configurada ? "Trocar chave" : "Colar chave"}
                    value={novasChaves[c.fornecedor] ?? ""}
                    onChange={(e) => setNovasChaves({ ...novasChaves, [c.fornecedor]: e.target.value })}
                  />
                  <button
                    type="button"
                    disabled={!novasChaves[c.fornecedor]?.trim()}
                    onClick={() => salvarChave(fornecedor)}
                  >
                    Salvar
                  </button>
                  {c.configurada && (
                    <button type="button" className="secundario" onClick={() => setRemover(fornecedor)}>
                      Remover
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {remover && (
        <div className="modal" onClick={() => setRemover(null)}>
          <div role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
            <h2>Remover chave</h2>
            <p>
              Remover a chave do <strong>{FORNECEDORES[remover].nome}</strong>?
            </p>
            <p className="suave" style={{ margin: 0 }}>
              {remover === "anthropic"
                ? "Sem ela, a qualificação e as fichas de abordagem param até uma nova chave ser cadastrada."
                : "Sem ela, a prospecção deixa de usar esse fornecedor."}
            </p>
            <div className="linha" style={{ justifyContent: "flex-end" }}>
              <button className="secundario" onClick={() => setRemover(null)}>
                Cancelar
              </button>
              <button onClick={confirmarRemocao}>Remover</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
