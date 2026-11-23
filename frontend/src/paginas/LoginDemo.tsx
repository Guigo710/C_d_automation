import { useEffect, useState } from "react";

import { api } from "../api/cliente";
import { entrarComoDemo, usuariosDeDemo, type UsuarioDeDemo } from "../autenticacao";
import { NOMES_DOS_PAPEIS } from "./MinhaOrganizacao";

export function LoginDemo() {
  const [usuarios, setUsuarios] = useState<UsuarioDeDemo[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    usuariosDeDemo()
      .then(setUsuarios)
      .catch(() => setErro("A API não respondeu. Ela está rodando com DEMO_LOCAL=true?"));
  }, []);

  async function entrar(id: string) {
    setErro(null);
    try {
      await entrarComoDemo(id);
      await api.POST("/eu/login").catch(() => undefined);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível entrar.");
    }
  }

  return (
    <main className="tela-de-entrada">
      <div className="cartao">
      <p className="rotulo">Demonstração local</p>
      <p className="marca">Commercial Department Automation</p>
      <h1>Entrar</h1>
      <p className="suave">Escolha com quem entrar. Os dados são fictícios.</p>
      {erro && <p className="erro">{erro}</p>}
      {!usuarios && !erro && <p>Carregando...</p>}
      <div className="lista-de-usuarios">
        {usuarios?.map((u) => (
          <button key={u.id} className="secundario" onClick={() => entrar(u.id)}>
            <strong>{u.nome}</strong>
            <span className="suave">
              {NOMES_DOS_PAPEIS[u.papel] ?? u.papel} · {u.organizacao}
            </span>
          </button>
        ))}
      </div>
    </div>
    </main>
  );
}
