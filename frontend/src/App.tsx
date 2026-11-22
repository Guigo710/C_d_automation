import { ProvedorDoEu, useEu } from "./eu";
import { CampanhaForm } from "./paginas/CampanhaForm";
import { Configuracao } from "./paginas/Configuracao";
import { Campanhas } from "./paginas/Campanhas";
import { Login } from "./paginas/Login";
import { MinhaOrganizacao, NOMES_DOS_PAPEIS } from "./paginas/MinhaOrganizacao";
import { NovaSenha } from "./paginas/NovaSenha";
import { irPara, useRota } from "./rota";
import { useSessao } from "./sessao";
import { supabase } from "./supabase";

export function App() {
  const { sessao, carregando, recuperandoSenha } = useSessao();

  if (carregando) return <main className="cartao">Carregando...</main>;
  if (recuperandoSenha) return <NovaSenha />;
  if (!sessao) return <Login />;
  return (
    <ProvedorDoEu>
      <Portal />
    </ProvedorDoEu>
  );
}

function Portal() {
  const { eu, erro } = useEu();
  const rota = useRota();

  if (erro) {
    return (
      <main className="cartao">
        <p className="erro">{erro}</p>
        <button className="link" onClick={() => supabase.auth.signOut()}>
          Sair
        </button>
      </main>
    );
  }
  if (!eu) return <main className="cartao">Carregando...</main>;

  return (
    <div className="portal">
      <nav className="menu">
        <strong>{eu.organizacao.nome}</strong>
        <a href="#/campanhas" className={rota.startsWith("/campanhas") ? "ativo" : ""}>
          Campanhas
        </a>
        <a href="#/organizacao" className={rota === "/organizacao" ? "ativo" : ""}>
          Minha organização
        </a>
        {eu.papel === "administrador" && (
          <a href="#/configuracao" className={rota === "/configuracao" ? "ativo" : ""}>
            Configuração
          </a>
        )}
        <span className="espaco" />
        <span className="suave">
          {eu.nome} · {NOMES_DOS_PAPEIS[eu.papel] ?? eu.papel}
        </span>
        <button className="link" onClick={() => supabase.auth.signOut()}>
          Sair
        </button>
      </nav>
      <main>{pagina(rota)}</main>
    </div>
  );
}

function pagina(rota: string) {
  if (rota === "/organizacao") return <MinhaOrganizacao />;
  if (rota === "/configuracao") return <Configuracao />;
  if (rota === "/campanhas/nova") return <CampanhaForm key="nova" campanhaId={null} />;
  const campanha = rota.match(/^\/campanhas\/([0-9a-f-]{36})$/);
  if (campanha) return <CampanhaForm key={campanha[1]} campanhaId={campanha[1]} />;
  if (rota !== "/campanhas") irPara("/campanhas");
  return <Campanhas />;
}
