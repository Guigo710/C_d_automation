import { useState, type FormEvent } from "react";

import { api } from "../api/cliente";
import { supabase } from "../supabase";

export function Login() {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function entrar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    setAviso(null);
    setEnviando(true);
    const { error } = await supabase().auth.signInWithPassword({ email, password: senha });
    setEnviando(false);
    if (error) {
      setErro("E-mail ou senha incorretos.");
      return;
    }
    // Registro do login na auditoria; uma falha aqui não impede o acesso.
    await api.POST("/eu/login").catch(() => undefined);
  }

  async function recuperarSenha() {
    setErro(null);
    setAviso(null);
    if (!email) {
      setErro("Digite seu e-mail para recuperar a senha.");
      return;
    }
    const { error } = await supabase().auth.resetPasswordForEmail(email, {
      redirectTo: window.location.origin,
    });
    if (error) setErro("Não foi possível enviar o e-mail de recuperação.");
    else setAviso("Se o e-mail estiver cadastrado, você vai receber um link para criar uma nova senha.");
  }

  return (
    <main className="tela-de-entrada">
      <div className="cartao">
      <p className="marca">Commercial Department Automation</p>
      <h1>Entrar</h1>
      <form onSubmit={entrar}>
        <label>
          E-mail
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Senha
          <input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} required />
        </label>
        {erro && <p className="erro">{erro}</p>}
        {aviso && <p className="aviso">{aviso}</p>}
        <button type="submit" disabled={enviando}>
          {enviando ? "Entrando..." : "Entrar"}
        </button>
        <button type="button" className="link" onClick={recuperarSenha}>
          Esqueci minha senha
        </button>
      </form>
    </div>
    </main>
  );
}
