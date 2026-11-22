import { Login } from "./paginas/Login";
import { MinhaOrganizacao } from "./paginas/MinhaOrganizacao";
import { NovaSenha } from "./paginas/NovaSenha";
import { useSessao } from "./sessao";

export function App() {
  const { sessao, carregando, recuperandoSenha } = useSessao();

  if (carregando) return <main className="cartao">Carregando...</main>;
  if (recuperandoSenha) return <NovaSenha />;
  if (!sessao) return <Login />;
  return <MinhaOrganizacao />;
}
