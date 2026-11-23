import { useCallback, useEffect, useState } from "react";

import { api } from "../api/cliente";
import type { components } from "../api/schema";
import { MOTIVOS_DE_RECUSA, NOMES_DOS_PAPEIS } from "../ui";

type Evento = components["schemas"]["EventoOut"];

const ACOES: Record<string, string> = {
  login: "Entrou no sistema",
  "candidatos.aprovados": "Aprovou candidatos",
  "candidato.recusado": "Recusou candidato",
  "candidato.restaurado": "Restaurou recusa sugerida",
  "candidato.tier_alterado": "Mudou o tier",
  "candidatos.promovidos": "Enviou para a operação",
  "empresa.assumida": "Assumiu empresa",
  "empresa.atribuida": "Atribuiu empresa",
  "empresa.transferida": "Transferiu empresa",
  "exportacao.aprovados": "Exportou aprovados (Excel)",
  "teto_mensal.alterado": "Mudou o teto mensal",
  "chave_api.alterada": "Salvou chave de API",
  "chave_api.removida": "Removeu chave de API",
};

function resumoDosDetalhes(evento: Evento): string {
  const d = evento.detalhes as Record<string, unknown>;
  if (Array.isArray(d.candidatos)) return `${d.candidatos.length} candidato(s)`;
  if (typeof d.motivo === "string") return `motivo: ${MOTIVOS_DE_RECUSA[d.motivo] ?? d.motivo}`;
  if (typeof d.tier === "string") return `para tier ${d.tier}${d.justificativa ? ` · ${d.justificativa}` : ""}`;
  if (typeof d.teto_mensal_usd === "string") return `US$ ${d.teto_mensal_usd}`;
  if (typeof d.linhas === "number") return `${d.linhas} linha(s)`;
  if (evento.recurso_tipo === "chave_api" && evento.recurso_id) return evento.recurso_id;
  return "";
}

export function Auditoria() {
  const [eventos, setEventos] = useState<Evento[]>([]);
  const [proximo, setProximo] = useState<number | null>(null);
  const [pessoas, setPessoas] = useState<Record<string, string>>({});
  const [carregando, setCarregando] = useState(false);

  const carregar = useCallback(async (antesDe?: number) => {
    setCarregando(true);
    const { data } = await api.GET("/auditoria", {
      params: { query: { limite: 50, antes_de: antesDe ?? null } },
    });
    setCarregando(false);
    if (!data) return;
    setEventos((atuais) => (antesDe ? [...atuais, ...data.itens] : data.itens));
    setProximo(data.proximo_antes_de ?? null);
  }, []);

  useEffect(() => {
    carregar();
    api.GET("/usuarios").then(({ data }) => {
      if (data)
        setPessoas(
          Object.fromEntries(data.map((u) => [u.id, `${u.nome} (${NOMES_DOS_PAPEIS[u.papel] ?? u.papel})`])),
        );
    });
  }, [carregar]);

  return (
    <>
      <header className="cabecalho">
        <div>
          <p className="rotulo">Administração</p>
          <h1>Auditoria</h1>
        </div>
      </header>
      <p className="suave" style={{ marginTop: -12 }}>
        Registro só de inclusões: o banco não deixa alterar nem apagar eventos.
      </p>

      <section className="painel">
        {eventos.length === 0 && !carregando ? (
          <p className="suave">Nenhum evento ainda.</p>
        ) : (
          <div className="tabela-rolavel">
            <table>
              <thead>
                <tr>
                  <th>Quando</th>
                  <th>Quem</th>
                  <th>O quê</th>
                  <th>Detalhes</th>
                </tr>
              </thead>
              <tbody>
                {eventos.map((e) => (
                  <tr key={e.id}>
                    <td className="mono suave" style={{ whiteSpace: "nowrap" }}>
                      {new Date(e.criado_em).toLocaleString("pt-BR")}
                    </td>
                    <td>{e.usuario_id ? (pessoas[e.usuario_id] ?? "usuário removido") : "sistema"}</td>
                    <td>{ACOES[e.acao] ?? e.acao}</td>
                    <td className="suave">{resumoDosDetalhes(e)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {proximo && (
          <button className="secundario" style={{ marginTop: 16 }} disabled={carregando} onClick={() => carregar(proximo)}>
            {carregando ? "Carregando..." : "Carregar mais"}
          </button>
        )}
      </section>
    </>
  );
}
