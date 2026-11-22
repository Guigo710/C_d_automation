import { useMemo, useState } from "react";

import type { components } from "../api/schema";

type Candidato = components["schemas"]["CandidatoResumo"];

const COLUNAS: { status: string; titulo: string }[] = [
  { status: "pendente", titulo: "Pendentes" },
  { status: "aprovado", titulo: "Aprovados" },
  { status: "recusado", titulo: "Recusados" },
];

const MOTIVOS: Record<string, string> = {
  fora_do_perfil: "Fora do perfil",
  cnpj_inativo: "CNPJ inativo",
  fora_da_regiao: "Fora da região",
  dados_incompletos: "Dados incompletos",
  ja_e_cliente: "Já é cliente",
  duplicado: "Duplicado",
  opt_out: "Não quer contato",
};

type Ordem = "nota" | "nome";

export function Kanban({
  candidatos,
  podeDecidir,
  aoAbrir,
  aoAprovar,
}: {
  candidatos: Candidato[];
  podeDecidir: boolean;
  aoAbrir: (id: string) => void;
  aoAprovar: (ids: string[]) => Promise<void>;
}) {
  const [selecionados, setSelecionados] = useState<Set<string>>(new Set());
  const [tier, setTier] = useState("");
  const [segmento, setSegmento] = useState("");
  const [ordem, setOrdem] = useState<Ordem>("nota");

  const segmentos = useMemo(
    () => [...new Set(candidatos.map((c) => c.empresa.segmento).filter(Boolean))] as string[],
    [candidatos],
  );
  const coletados = candidatos.filter((c) => c.status === "coletado").length;

  const visiveis = candidatos
    .filter((c) => !tier || (c.tier_final ?? c.tier_sugerido) === tier)
    .filter((c) => !segmento || c.empresa.segmento === segmento)
    .sort((a, b) =>
      ordem === "nota"
        ? (b.nota_total ?? -1) - (a.nota_total ?? -1)
        : (a.empresa.nome_fantasia ?? a.empresa.razao_social).localeCompare(
            b.empresa.nome_fantasia ?? b.empresa.razao_social,
          ),
    );

  function alternar(id: string) {
    const novo = new Set(selecionados);
    if (novo.has(id)) novo.delete(id);
    else novo.add(id);
    setSelecionados(novo);
  }

  async function aprovar() {
    await aoAprovar([...selecionados]);
    setSelecionados(new Set());
  }

  return (
    <div>
      <div className="linha filtros">
        <label>
          Tier
          <select value={tier} onChange={(e) => setTier(e.target.value)}>
            <option value="">Todos</option>
            <option value="A">A</option>
            <option value="B">B</option>
            <option value="C">C</option>
          </select>
        </label>
        <label>
          Segmento
          <select value={segmento} onChange={(e) => setSegmento(e.target.value)}>
            <option value="">Todos</option>
            {segmentos.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label>
          Ordenar por
          <select value={ordem} onChange={(e) => setOrdem(e.target.value as Ordem)}>
            <option value="nota">Nota</option>
            <option value="nome">Nome</option>
          </select>
        </label>
        {podeDecidir && (
          <button disabled={selecionados.size === 0} onClick={aprovar}>
            Aprovar selecionados ({selecionados.size})
          </button>
        )}
      </div>
      {coletados > 0 && <p className="suave">{coletados} empresa(s) aguardando qualificação.</p>}

      <div className="kanban">
        {COLUNAS.map((coluna) => {
          const cartoes = visiveis.filter((c) => c.status === coluna.status);
          return (
            <section key={coluna.status} className="coluna">
              <h3>
                {coluna.titulo} <span className="suave">({cartoes.length})</span>
              </h3>
              {cartoes.map((c) => (
                <article key={c.id} className="cartao-kanban" onClick={() => aoAbrir(c.id)}>
                  <header>
                    {podeDecidir && coluna.status === "pendente" && (
                      <input
                        type="checkbox"
                        checked={selecionados.has(c.id)}
                        onClick={(e) => e.stopPropagation()}
                        onChange={() => alternar(c.id)}
                        aria-label="Selecionar para aprovar"
                      />
                    )}
                    <strong>{c.empresa.nome_fantasia ?? c.empresa.razao_social}</strong>
                  </header>
                  <p className="suave">{c.empresa.segmento}</p>
                  <p>
                    <span className="etiqueta">Tier {c.tier_final ?? c.tier_sugerido ?? "—"}</span>{" "}
                    {c.nota_total != null && <span className="suave">nota {c.nota_total}</span>}
                    {c.baixa_confianca && <span className="etiqueta alerta">baixa confiança</span>}
                    {c.em_revisao && <span className="etiqueta alerta">revisão</span>}
                  </p>
                  {c.motivo_recusa && (
                    <p className="suave">
                      {MOTIVOS[c.motivo_recusa] ?? c.motivo_recusa}
                      {c.recusa_sugerida && " · sugerido"}
                    </p>
                  )}
                </article>
              ))}
            </section>
          );
        })}
      </div>
    </div>
  );
}
