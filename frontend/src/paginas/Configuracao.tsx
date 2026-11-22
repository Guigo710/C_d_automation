import { useEffect, useState, type FormEvent } from "react";

import { api } from "../api/cliente";
import type { components } from "../api/schema";

type Configuracao = components["schemas"]["ConfiguracaoDaOrganizacao"];
type Fornecedor = "anthropic" | "google_places" | "brave";

const NOMES_DOS_FORNECEDORES: Record<string, string> = {
  anthropic: "Claude API (Anthropic)",
  google_places: "Google Places",
  brave: "Brave Search",
};

export function Configuracao() {
  const [config, setConfig] = useState<Configuracao | null>(null);
  const [teto, setTeto] = useState("");
  const [novasChaves, setNovasChaves] = useState<Record<string, string>>({});
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
      setMensagem({ tipo: "aviso", texto: "Chave salva." });
    } else if (response.status === 503) {
      setMensagem({ tipo: "erro", texto: "O servidor não tem a cifragem de chaves configurada." });
    } else setMensagem({ tipo: "erro", texto: "Não foi possível salvar a chave." });
  }

  async function removerChave(fornecedor: Fornecedor) {
    const { data } = await api.DELETE("/configuracao/chaves/{fornecedor}", {
      params: { path: { fornecedor } },
    });
    if (data) aplicar(data);
  }

  if (!config) return <section className="painel">Carregando...</section>;

  const gasto = Number(config.gasto_do_mes_usd);
  const limite = Number(config.teto_mensal_usd);

  return (
    <section className="painel">
      <h1>Configuração da organização</h1>
      {mensagem && <p className={mensagem.tipo}>{mensagem.texto}</p>}

      <h2>Teto de gasto mensal</h2>
      <p className="suave">
        Gasto do mês com dados e IA: <strong>US$ {gasto.toFixed(2)}</strong> de US$ {limite.toFixed(2)}
        {limite > 0 && ` (${Math.min(100, (gasto / limite) * 100).toFixed(0)}%)`}
      </p>
      <form onSubmit={salvarTeto} className="linha">
        <label>
          Teto (US$)
          <input type="number" min={0} step="0.01" value={teto} onChange={(e) => setTeto(e.target.value)} />
        </label>
        <button type="submit">Salvar teto</button>
      </form>

      <h2>Chaves de API</h2>
      <p className="suave">
        As chaves ficam cifradas no servidor e nunca são mostradas de novo; aparece só o final.
      </p>
      <table>
        <tbody>
          {config.chaves.map((c) => {
            const fornecedor = c.fornecedor as Fornecedor;
            return (
              <tr key={c.fornecedor}>
                <td>{NOMES_DOS_FORNECEDORES[c.fornecedor] ?? c.fornecedor}</td>
                <td>{c.configurada ? `configurada (…${c.final})` : <span className="suave">não configurada</span>}</td>
                <td>
                  <div className="linha">
                    <input
                      type="password"
                      autoComplete="off"
                      placeholder={c.configurada ? "Trocar chave" : "Colar chave"}
                      value={novasChaves[c.fornecedor] ?? ""}
                      onChange={(e) => setNovasChaves({ ...novasChaves, [c.fornecedor]: e.target.value })}
                    />
                    <button type="button" onClick={() => salvarChave(fornecedor)}>
                      Salvar
                    </button>
                    {c.configurada && (
                      <button type="button" className="link" onClick={() => removerChave(fornecedor)}>
                        Remover
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
