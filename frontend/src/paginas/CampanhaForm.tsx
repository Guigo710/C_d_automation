import { useEffect, useState, type FormEvent } from "react";

import { api } from "../api/cliente";
import type { components } from "../api/schema";
import { useEu } from "../eu";
import { irPara } from "../rota";
import { NOMES_DOS_STATUS } from "./Campanhas";

type CampanhaIn = components["schemas"]["CampanhaIn"];
type Segmento = components["schemas"]["SegmentoOut"];
type Municipio = components["schemas"]["MunicipioOut"];
type Usuario = components["schemas"]["UsuarioOut"];
type Tier = CampanhaIn["tiers_alvo"][number];
type Status = NonNullable<CampanhaIn["status"]>;

const TIERS: Tier[] = ["A", "B", "C"];
const STATUS: Status[] = ["rascunho", "ativa", "pausada", "encerrada"];

const VAZIA: CampanhaIn = {
  nome: "",
  status: "rascunho",
  municipios_ibge: [],
  segmento_ids: [],
  tiers_alvo: ["A", "B", "C"],
  limite_empresas: 300,
  teto_gasto_usd: "10.00",
  membro_ids: [],
};

function alternar<T>(lista: T[], item: T): T[] {
  return lista.includes(item) ? lista.filter((x) => x !== item) : [...lista, item];
}

export function CampanhaForm({ campanhaId }: { campanhaId: string | null }) {
  const { eu } = useEu();
  const podeEditar = eu?.papel === "coordenador";
  const [campanha, setCampanha] = useState<CampanhaIn | null>(campanhaId ? null : VAZIA);
  const [segmentos, setSegmentos] = useState<Segmento[]>([]);
  const [municipios, setMunicipios] = useState<Municipio[]>([]);
  const [vendedores, setVendedores] = useState<Usuario[]>([]);
  const [outrosMunicipios, setOutrosMunicipios] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    api.GET("/catalogo-segmentos").then(({ data }) => data && setSegmentos(data));
    api.GET("/municipios-atendidos").then(({ data }) => data && setMunicipios(data));
    if (podeEditar) {
      api
        .GET("/usuarios", { params: { query: { papel: "vendedor" } } })
        .then(({ data }) => data && setVendedores(data));
    }
  }, [podeEditar]);

  useEffect(() => {
    if (!campanhaId) return;
    api.GET("/campanhas/{campanha_id}", { params: { path: { campanha_id: campanhaId } } }).then(
      ({ data }) => {
        if (!data) {
          setErro("Campanha não encontrada.");
          return;
        }
        setCampanha({
          nome: data.nome,
          status: data.status,
          municipios_ibge: data.municipios_ibge,
          segmento_ids: data.segmentos.map((s) => s.id),
          tiers_alvo: data.tiers_alvo,
          limite_empresas: data.limite_empresas,
          teto_gasto_usd: data.teto_gasto_usd,
          membro_ids: data.membros.map((m) => m.id),
        });
        if (!podeEditar) setVendedores(data.membros.map((m) => ({ ...m, email: "", papel: "vendedor", ativo: true })));
      },
    );
  }, [campanhaId, podeEditar]);

  if (!campanha) return <section className="painel">{erro ?? "Carregando..."}</section>;

  const atendidos = new Set(municipios.map((m) => m.municipio_ibge));
  const extras = campanha.municipios_ibge.filter((m) => !atendidos.has(m));
  const mudar = (parte: Partial<CampanhaIn>) => setCampanha({ ...campanha, ...parte });

  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    if (!campanha) return;
    setErro(null);
    const codigosExtras = outrosMunicipios
      .split(/[\s,;]+/)
      .map((c) => c.trim())
      .filter(Boolean);
    const corpo: CampanhaIn = {
      ...campanha,
      municipios_ibge: [...new Set([...campanha.municipios_ibge, ...codigosExtras])],
    };
    setSalvando(true);
    const { data, error } = campanhaId
      ? await api.PUT("/campanhas/{campanha_id}", {
          params: { path: { campanha_id: campanhaId } },
          body: corpo,
        })
      : await api.POST("/campanhas", { body: corpo });
    setSalvando(false);
    if (data) irPara("/campanhas");
    else setErro(typeof error?.detail === "string" ? error.detail : "Confira os campos da campanha.");
  }

  return (
    <section className="painel">
      <header className="cabecalho-da-pagina">
        <h1>{campanhaId ? campanha.nome || "Campanha" : "Nova campanha"}</h1>
        <button className="link" onClick={() => irPara("/campanhas")}>
          Voltar
        </button>
      </header>
      <form onSubmit={salvar}>
        <fieldset disabled={!podeEditar}>
          <label>
            Nome
            <input value={campanha.nome} onChange={(e) => mudar({ nome: e.target.value })} required />
          </label>

          {campanhaId && (
            <label>
              Status
              <select value={campanha.status} onChange={(e) => mudar({ status: e.target.value as Status })}>
                {STATUS.map((s) => (
                  <option key={s} value={s}>
                    {NOMES_DOS_STATUS[s]}
                  </option>
                ))}
              </select>
            </label>
          )}

          <div className="grupo">
            <span>Municípios</span>
            {municipios.map((m) => (
              <label key={m.municipio_ibge} className="opcao">
                <input
                  type="checkbox"
                  checked={campanha.municipios_ibge.includes(m.municipio_ibge)}
                  onChange={() => mudar({ municipios_ibge: alternar(campanha.municipios_ibge, m.municipio_ibge) })}
                />
                {m.nome} ({m.uf}){m.tem_rota ? " · com rota" : ""}
              </label>
            ))}
            {extras.map((codigo) => (
              <label key={codigo} className="opcao">
                <input
                  type="checkbox"
                  checked
                  onChange={() => mudar({ municipios_ibge: alternar(campanha.municipios_ibge, codigo) })}
                />
                Código IBGE {codigo}
              </label>
            ))}
            <label>
              Outros municípios (códigos IBGE de 7 dígitos, separados por vírgula)
              <input value={outrosMunicipios} onChange={(e) => setOutrosMunicipios(e.target.value)} />
            </label>
          </div>

          <div className="grupo">
            <span>Segmentos</span>
            {segmentos.map((s) => (
              <label key={s.id} className="opcao">
                <input
                  type="checkbox"
                  checked={campanha.segmento_ids.includes(s.id)}
                  onChange={() => mudar({ segmento_ids: alternar(campanha.segmento_ids, s.id) })}
                />
                {s.nome}
              </label>
            ))}
          </div>

          <div className="grupo">
            <span>Tiers-alvo</span>
            <div className="linha">
              {TIERS.map((t) => (
                <label key={t} className="opcao">
                  <input
                    type="checkbox"
                    checked={campanha.tiers_alvo.includes(t)}
                    onChange={() => mudar({ tiers_alvo: alternar(campanha.tiers_alvo, t) })}
                  />
                  Tier {t}
                </label>
              ))}
            </div>
          </div>

          <div className="linha">
            <label>
              Limite de empresas
              <input
                type="number"
                min={1}
                value={campanha.limite_empresas}
                onChange={(e) => mudar({ limite_empresas: Number(e.target.value) })}
              />
            </label>
            <label>
              Teto de gasto (US$)
              <input
                type="number"
                min={0}
                step="0.01"
                value={campanha.teto_gasto_usd}
                onChange={(e) => mudar({ teto_gasto_usd: e.target.value })}
              />
            </label>
          </div>

          <div className="grupo">
            <span>Vendedores participantes</span>
            {vendedores.length === 0 && <p className="suave">Nenhum vendedor.</p>}
            {vendedores.map((v) => (
              <label key={v.id} className="opcao">
                <input
                  type="checkbox"
                  checked={(campanha.membro_ids ?? []).includes(v.id)}
                  onChange={() => mudar({ membro_ids: alternar(campanha.membro_ids ?? [], v.id) })}
                />
                {v.nome}
              </label>
            ))}
          </div>
        </fieldset>

        {erro && <p className="erro">{erro}</p>}
        {podeEditar && (
          <button type="submit" disabled={salvando}>
            {salvando ? "Salvando..." : "Salvar campanha"}
          </button>
        )}
      </form>
    </section>
  );
}
