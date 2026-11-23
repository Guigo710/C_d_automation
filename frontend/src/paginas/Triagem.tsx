import { useCallback, useEffect, useMemo, useState, type DragEvent } from "react";

import { api } from "../api/cliente";
import type { components } from "../api/schema";
import { useEu } from "../eu";
import {
  BarraDeNota,
  Kpi,
  MOTIVOS_DE_RECUSA,
  NOMES_DAS_FONTES,
  Tier,
  formatarCnpj,
  useMunicipios,
} from "../ui";
import { GavetaDoCandidato } from "./GavetaDoCandidato";

type Candidato = components["schemas"]["CandidatoResumo"];
type CandidatoDetalhe = components["schemas"]["CandidatoDetalhe"];
type Motivo = components["schemas"]["RecusaIn"]["motivo"];
type Destino = "A" | "B" | "C" | "recusados";

const tierDe = (c: Candidato) => c.tier_final ?? c.tier_sugerido;

export function Triagem({ campanhaId }: { campanhaId: string }) {
  const { eu } = useEu();
  const municipios = useMunicipios();
  const podeDecidir = eu?.papel === "coordenador";
  const [candidatos, setCandidatos] = useState<Candidato[]>([]);
  const [selecionados, setSelecionados] = useState<Set<string>>(new Set());
  const [segmento, setSegmento] = useState("");
  const [busca, setBusca] = useState("");
  const [aberto, setAberto] = useState<CandidatoDetalhe | null>(null);
  const [arrastando, setArrastando] = useState<string | null>(null);
  const [sobre, setSobre] = useState<Destino | null>(null);
  const [pendencia, setPendencia] = useState<{ candidato: Candidato; destino: Destino } | null>(null);
  const [mensagem, setMensagem] = useState<{ tipo: "erro" | "aviso"; texto: string } | null>(null);
  const caminho = { params: { path: { campanha_id: campanhaId } } };

  const carregar = useCallback(async () => {
    const { data } = await api.GET("/campanhas/{campanha_id}/candidatos", {
      params: { path: { campanha_id: campanhaId }, query: { limite: 200 } },
    });
    if (data) setCandidatos(data.itens);
  }, [campanhaId]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const coletados = candidatos.filter((c) => c.status === "coletado").length;
  useEffect(() => {
    if (coletados === 0) return;
    const id = window.setInterval(carregar, 3000);
    return () => window.clearInterval(id);
  }, [coletados, carregar]);

  const cidade = (codigo: string | null | undefined) => (codigo ? (municipios[codigo] ?? codigo) : "–");
  const segmentos = useMemo(
    () => [...new Set(candidatos.map((c) => c.empresa.segmento).filter(Boolean))] as string[],
    [candidatos],
  );
  const visiveis = candidatos
    .filter((c) => c.status !== "coletado")
    .filter((c) => !segmento || c.empresa.segmento === segmento)
    .filter((c) => {
      const termo = busca.trim().toLowerCase();
      return !termo || `${c.empresa.nome_fantasia} ${c.empresa.razao_social}`.toLowerCase().includes(termo);
    })
    .sort((a, b) => (b.nota_total ?? -1) - (a.nota_total ?? -1));

  const aprovados = candidatos.filter((c) => c.status === "aprovado");
  const pendentes = candidatos.filter((c) => c.status === "pendente");
  const recusados = candidatos.filter((c) => c.status === "recusado");

  function avisar(tipo: "erro" | "aviso", texto: string) {
    setMensagem({ tipo, texto });
    window.setTimeout(() => setMensagem(null), 4000);
  }

  async function abrir(id: string) {
    const { data } = await api.GET("/candidatos/{candidato_id}", {
      params: { path: { candidato_id: id } },
    });
    if (data) setAberto(data);
  }

  async function aprovar(ids: string[]) {
    if (ids.length === 0) return;
    const { error } = await api.POST("/campanhas/{campanha_id}/aprovacoes", {
      ...caminho,
      body: { candidato_ids: ids },
    });
    if (error) avisar("erro", "Não foi possível aprovar.");
    setSelecionados(new Set());
    await carregar();
  }

  async function subirParaOperacao() {
    const { data, error } = await api.POST("/campanhas/{campanha_id}/promocoes", {
      params: {
        path: { campanha_id: campanhaId },
        // Uma chave nova por clique: repetir o mesmo pedido não duplica nada.
        header: { "Idempotency-Key": crypto.randomUUID() },
      },
      body: { candidato_ids: aprovados.map((c) => c.id) },
    });
    if (error || !data) avisar("erro", "Não foi possível enviar para a operação.");
    else avisar("aviso", `${data.promovidas.length} empresa(s) enviada(s) para os vendedores.`);
    await carregar();
  }

  async function exportar() {
    const { data, error } = await api.GET("/campanhas/{campanha_id}/aprovados.xlsx", {
      ...caminho,
      parseAs: "blob",
    });
    if (error || !data) return avisar("erro", "Não foi possível exportar.");
    const url = URL.createObjectURL(data as Blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "aprovados.xlsx";
    link.click();
    URL.revokeObjectURL(url);
  }

  // --- arrastar entre colunas: muda o tier (com justificativa) ou recusa (com motivo) ---

  function aoSoltar(destino: Destino) {
    setSobre(null);
    const candidato = candidatos.find((c) => c.id === arrastando);
    setArrastando(null);
    if (!candidato || !podeDecidir) return;
    if (destino === "recusados" && candidato.status === "aprovado") {
      return avisar("erro", "Candidato aprovado não pode ser recusado.");
    }
    if (destino !== "recusados" && candidato.status === "recusado") {
      return avisar("erro", "Para tirar dos recusados, abra o candidato e restaure a recusa sugerida.");
    }
    if (destino !== "recusados" && tierDe(candidato) === destino) return;
    setPendencia({ candidato, destino });
  }

  async function confirmar(texto: string) {
    if (!pendencia) return;
    const { candidato, destino } = pendencia;
    const caminhoDoCandidato = { params: { path: { candidato_id: candidato.id } } };
    const { error } =
      destino === "recusados"
        ? await api.POST("/candidatos/{candidato_id}/recusa", {
            ...caminhoDoCandidato,
            body: { motivo: texto as Motivo },
          })
        : await api.PUT("/candidatos/{candidato_id}/tier", {
            ...caminhoDoCandidato,
            body: { tier: destino, justificativa: texto },
          });
    setPendencia(null);
    if (error) avisar("erro", "Não foi possível concluir a mudança.");
    await carregar();
  }

  function propsDeColuna(destino: Destino) {
    if (!podeDecidir) return {};
    return {
      onDragOver: (e: DragEvent) => {
        e.preventDefault();
        setSobre(destino);
      },
      onDragLeave: () => setSobre((atual) => (atual === destino ? null : atual)),
      onDrop: (e: DragEvent) => {
        e.preventDefault();
        aoSoltar(destino);
      },
    };
  }

  function cartao(c: Candidato) {
    const tier = tierDe(c);
    const recusado = c.status === "recusado";
    return (
      <article
        key={c.id}
        className={`card-empresa ${recusado ? "" : (tier ?? "")}`}
        draggable={podeDecidir && c.status !== "coletado"}
        onDragStart={() => setArrastando(c.id)}
        onDragEnd={() => setArrastando(null)}
        onClick={() => abrir(c.id)}
      >
        <header>
          {podeDecidir && c.status === "pendente" && (
            <input
              type="checkbox"
              aria-label="Selecionar para aprovar"
              checked={selecionados.has(c.id)}
              onClick={(e) => e.stopPropagation()}
              onChange={() => {
                const novo = new Set(selecionados);
                if (novo.has(c.id)) novo.delete(c.id);
                else novo.add(c.id);
                setSelecionados(novo);
              }}
            />
          )}
          <strong>{c.empresa.nome_fantasia ?? c.empresa.razao_social}</strong>
          {!recusado && <Tier tier={tier} />}
        </header>
        <p className="meta">
          {cidade(c.empresa.municipio_ibge)} · {c.empresa.segmento}
          <br />
          <span className="mono">{formatarCnpj(c.empresa.cnpj)}</span>
        </p>
        {!recusado && <BarraDeNota nota={c.nota_total} />}
        <div className="rodape-card">
          {c.origens.map((o) => (
            <span key={o} className="etiqueta">
              {NOMES_DAS_FONTES[o] ?? o}
            </span>
          ))}
          {c.status === "aprovado" && <span className="etiqueta sucesso">aprovado</span>}
          {c.baixa_confianca && <span className="etiqueta alerta">baixa confiança</span>}
          {c.em_revisao && <span className="etiqueta perigo">revisão</span>}
          {c.motivo_recusa && (
            <span className="etiqueta perigo">
              {MOTIVOS_DE_RECUSA[c.motivo_recusa] ?? c.motivo_recusa}
              {c.recusa_sugerida ? " · sugerido" : ""}
            </span>
          )}
        </div>
      </article>
    );
  }

  const colunas: { destino: Destino; titulo: string }[] = [
    { destino: "A", titulo: "Tier A" },
    { destino: "B", titulo: "Tier B" },
    { destino: "C", titulo: "Tier C" },
  ];

  return (
    <>
      <header className="cabecalho">
        <div>
          <p className="rotulo">Dashboard da rodada</p>
          <h1>Triagem</h1>
        </div>
        {podeDecidir && (
          <div className="acoes-do-topo">
            <button className="secundario" onClick={exportar} disabled={aprovados.length === 0}>
              Exportar aprovados (Excel)
            </button>
            <button onClick={subirParaOperacao} disabled={aprovados.length === 0}>
              Subir {aprovados.length} para operação
            </button>
          </div>
        )}
      </header>

      <div className="kpis">
        <Kpi rotulo="Encontradas" valor={candidatos.length} />
        <Kpi rotulo="Na triagem" valor={pendentes.length} destaque />
        <Kpi rotulo="Aprovadas" valor={aprovados.length} />
        <Kpi rotulo="Recusadas" valor={recusados.length} />
        <Kpi rotulo="Tier A" valor={candidatos.filter((c) => c.status !== "recusado" && tierDe(c) === "A").length} />
      </div>

      {coletados > 0 && (
        <p className="etiqueta alerta" style={{ marginBottom: 16 }}>
          {coletados} empresa(s) aguardando a qualificação dos agentes
        </p>
      )}
      {mensagem && <p className={mensagem.tipo}>{mensagem.texto}</p>}

      <div className="barra-de-filtros">
        <label>
          Buscar
          <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Nome da empresa" />
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
        {podeDecidir && (
          <button
            className="secundario"
            disabled={selecionados.size === 0}
            onClick={() => aprovar([...selecionados])}
          >
            Aprovar selecionados ({selecionados.size})
          </button>
        )}
        {podeDecidir && <span className="suave">Arraste um card entre colunas para mudar o tier ou recusar.</span>}
      </div>

      {candidatos.length === 0 ? (
        <div className="painel">
          <p className="suave">Nenhuma empresa ainda. Inicie a prospecção na aba Execução.</p>
        </div>
      ) : (
        <div className="kanban">
          {colunas.map(({ destino, titulo }) => {
            const lista = visiveis.filter(
              (c) => c.status !== "recusado" && (tierDe(c) ?? "C") === destino,
            );
            return (
              <section
                key={destino}
                className={`coluna${sobre === destino ? " recebendo" : ""}`}
                {...propsDeColuna(destino)}
              >
                <header>
                  <Tier tier={destino} />
                  <h3>{titulo}</h3>
                  <span className="mono suave">{lista.length}</span>
                </header>
                {lista.map(cartao)}
              </section>
            );
          })}
          <section
            className={`coluna recusados${sobre === "recusados" ? " recebendo" : ""}`}
            {...propsDeColuna("recusados")}
          >
            <header>
              <h3>Recusados</h3>
              <span className="mono suave">{visiveis.filter((c) => c.status === "recusado").length}</span>
            </header>
            {visiveis.filter((c) => c.status === "recusado").map(cartao)}
          </section>
        </div>
      )}

      {pendencia && (
        <ModalDeDecisao
          destino={pendencia.destino}
          nome={pendencia.candidato.empresa.nome_fantasia ?? pendencia.candidato.empresa.razao_social}
          aoConfirmar={confirmar}
          aoCancelar={() => setPendencia(null)}
        />
      )}

      {aberto && (
        <GavetaDoCandidato
          candidato={aberto}
          cidade={cidade(aberto.empresa.municipio_ibge)}
          podeDecidir={podeDecidir}
          aoFechar={() => setAberto(null)}
          aoMudar={async () => {
            await carregar();
            await abrir(aberto.id);
          }}
        />
      )}
    </>
  );
}

function ModalDeDecisao({
  destino,
  nome,
  aoConfirmar,
  aoCancelar,
}: {
  destino: Destino;
  nome: string;
  aoConfirmar: (texto: string) => void;
  aoCancelar: () => void;
}) {
  const recusa = destino === "recusados";
  const [texto, setTexto] = useState(recusa ? "fora_do_perfil" : "");
  return (
    <div className="modal" onClick={aoCancelar}>
      <div onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        <h2>{recusa ? "Recusar empresa" : `Mudar para Tier ${destino}`}</h2>
        <p className="suave">{nome}</p>
        {recusa ? (
          <label>
            Motivo da recusa
            <select value={texto} onChange={(e) => setTexto(e.target.value)}>
              {Object.entries(MOTIVOS_DE_RECUSA).map(([valor, rotulo]) => (
                <option key={valor} value={valor}>
                  {rotulo}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <label>
            Justificativa (obrigatória)
            <input autoFocus value={texto} onChange={(e) => setTexto(e.target.value)} />
          </label>
        )}
        <div className="linha" style={{ justifyContent: "flex-end" }}>
          <button className="secundario" onClick={aoCancelar}>
            Cancelar
          </button>
          <button disabled={!recusa && texto.trim().length < 3} onClick={() => aoConfirmar(texto)}>
            Confirmar
          </button>
        </div>
      </div>
    </div>
  );
}
