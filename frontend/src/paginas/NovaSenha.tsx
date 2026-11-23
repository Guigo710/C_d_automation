import { useState, type FormEvent } from "react";

import { supabase } from "../supabase";

export function NovaSenha() {
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [pronto, setPronto] = useState(false);

  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    const { error } = await supabase().auth.updateUser({ password: senha });
    if (error) setErro("Não foi possível salvar a nova senha.");
    else setPronto(true);
  }

  if (pronto) {
    return (
      <main className="cartao">
        <p>Senha alterada. Você já está conectado.</p>
        <button onClick={() => window.location.assign("/")}>Continuar</button>
      </main>
    );
  }

  return (
    <main className="cartao">
      <h1>Criar nova senha</h1>
      <form onSubmit={salvar}>
        <label>
          Nova senha
          <input
            type="password"
            minLength={8}
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            required
          />
        </label>
        {erro && <p className="erro">{erro}</p>}
        <button type="submit">Salvar</button>
      </form>
    </main>
  );
}
