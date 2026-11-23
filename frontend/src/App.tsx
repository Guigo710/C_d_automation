import { useEffect, useState } from "react";

import { api } from "./api/cliente";
import { MODO_DEMO, sair } from "./autenticacao";
import { ProvedorDoEu, useEu } from "./eu";
import { CampanhaForm } from "./paginas/CampanhaForm";
import { Campanhas } from "./paginas/Campanhas";
import { Clientes } from "./paginas/Clientes";
import { Configuracao } from "./paginas/Configuracao";
import { Execucao } from "./paginas/Execucao";
import { Login } from "./paginas/Login";
import { LoginDemo } from "./paginas/LoginDemo";
import { MinhaOrganizacao } from "./paginas/MinhaOrganizacao";
import { NovaSenha } from "./paginas/NovaSenha";
import { Operacao } from "./paginas/Operacao";
import { ProspeccaoVendedor } from "./paginas/ProspeccaoVendedor";
import { Triagem } from "./paginas/Triagem";
import { irPara, useRota } from "./rota";
import { useSessao } from "./sessao";
import { NOMES_DOS_PAPEIS } from "./ui";

export function App() {
  const { logado, carregando, recuperandoSenha } = useSessao();

  if (carregando) return <main className="tela-de-entrada">Carregando...</main>;
  if (recuperandoSenha) return <NovaSenha />;
  if (!logado) return MODO_DEMO ? <LoginDemo /> : <Login />;
  return (
    <ProvedorDoEu>
      <Portal />
    </ProvedorDoEu>
  );
}

// Rotas: #/campanhas, #/campanhas/nova, #/campanhas/<id>/<aba>, #/clientes, #/configuracao,
// #/organizacao. Sem aba, a campanha abre na triagem (coordenador) ou na prospecção (vendedor).
function interpretar(rota: string): { campanhaId: string | null; aba: string } {
  const m = rota.match(/^\/campanhas\/([0-9a-f-]{36})(?:\/(\w+))?$/);
  if (m) return { campanhaId: m[1], aba: m[2] ?? "" };
  return { campanhaId: null, aba: rota };
}

function Portal() {
  const { eu, erro } = useEu();
  const rota = useRota();
  const { campanhaId, aba } = interpretar(rota);
  const [nomeDaCampanha, setNomeDaCampanha] = useState<string | null>(null);

  useEffect(() => {
    setNomeDaCampanha(null);
    if (!campanhaId) return;
    api
      .GET("/campanhas/{campanha_id}", { params: { path: { campanha_id: campanhaId } } })
      .then(({ data }) => setNomeDaCampanha(data?.nome ?? null));
  }, [campanhaId]);

  if (erro) {
    return (
      <main className="tela-de-entrada">
        <div className="cartao">
          <p className="erro">{erro}</p>
          <button className="link" onClick={() => sair()}>
            Sair
          </button>
        </div>
      </main>
    );
  }
  if (!eu) return <main className="tela-de-entrada">Carregando...</main>;

  const papel = eu.papel;
  const abaAtual = campanhaId ? aba || (papel === "vendedor" ? "prospeccao" : "triagem") : aba;
  const abasDaCampanha: [string, string][] =
    papel === "vendedor"
      ? [["prospeccao", "Prospecção"]]
      : [
          ["triagem", "Triagem"],
          ["execucao", "Execução"],
          ["operacao", "Operação"],
          ["editar", papel === "coordenador" ? "Configurar campanha" : "Dados da campanha"],
        ];

  const link = (destino: string, texto: string, ativo: boolean) => (
    <a key={destino} href={`#${destino}`} className={ativo ? "ativo" : ""} aria-current={ativo ? "page" : undefined}>
      {texto}
    </a>
  );

  return (
    <div className="portal">
      <nav className="lateral" aria-label="Menu principal">
        <div className="marca">{eu.organizacao.nome}</div>
        {link("/campanhas", "Campanhas", rota === "/campanhas" || rota === "/campanhas/nova")}
        {papel === "vendedor" && link("/clientes", "Meus clientes", rota === "/clientes")}

        {campanhaId && (
          <>
            <p className="rotulo secao">Campanha</p>
            <p className="campanha-atual" title={nomeDaCampanha ?? ""}>
              {nomeDaCampanha ?? "…"}
            </p>
            {abasDaCampanha.map(([id, texto]) => link(`/campanhas/${campanhaId}/${id}`, texto, abaAtual === id))}
          </>
        )}

        <p className="rotulo secao">Organização</p>
        {papel === "administrador" && link("/configuracao", "Configuração", rota === "/configuracao")}
        {link("/organizacao", "Meu perfil", rota === "/organizacao")}

        <div className="rodape">
          <div>{eu.nome}</div>
          <div className="suave">{NOMES_DOS_PAPEIS[papel] ?? papel}</div>
          <button className="link" onClick={() => sair()}>
            Sair
          </button>
        </div>
      </nav>
      <main className="trabalho">{pagina(rota, campanhaId, abaAtual, papel)}</main>
    </div>
  );
}

function pagina(rota: string, campanhaId: string | null, aba: string, papel: string) {
  if (campanhaId) {
    if (papel === "vendedor") return <ProspeccaoVendedor key={campanhaId} campanhaId={campanhaId} />;
    if (aba === "execucao") return <Execucao key={campanhaId} campanhaId={campanhaId} />;
    if (aba === "operacao") return <Operacao key={campanhaId} campanhaId={campanhaId} />;
    if (aba === "editar") return <CampanhaForm key={campanhaId} campanhaId={campanhaId} />;
    return <Triagem key={campanhaId} campanhaId={campanhaId} />;
  }
  if (rota === "/campanhas/nova") return <CampanhaForm key="nova" campanhaId={null} />;
  if (rota === "/clientes" && papel === "vendedor") return <Clientes />;
  if (rota === "/configuracao" && papel === "administrador") return <Configuracao />;
  if (rota === "/organizacao") return <MinhaOrganizacao />;
  if (rota !== "/campanhas") irPara("/campanhas");
  return <Campanhas />;
}
