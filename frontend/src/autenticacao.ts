// Autenticação em dois modos: Supabase Auth (normal) ou demonstração local (VITE_DEMO_LOCAL),
// em que a própria API emite o token de um usuário de demonstração. O modo demo só existe
// quando a API roda com DEMO_LOCAL=true em localhost.
import { supabase } from "./supabase";

export const MODO_DEMO = import.meta.env.VITE_DEMO_LOCAL === "true";
const URL_DA_API = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";
const CHAVE_DO_TOKEN_DEMO = "cda-demo-token";

export type EventoDeSessao = "entrou" | "saiu" | "recuperacao";
type Ouvinte = (evento: EventoDeSessao) => void;

const ouvintes = new Set<Ouvinte>();
const avisar = (evento: EventoDeSessao) => ouvintes.forEach((o) => o(evento));

function tokenDemo(): string | null {
  try {
    return sessionStorage.getItem(CHAVE_DO_TOKEN_DEMO);
  } catch {
    return null;
  }
}

export async function obterToken(): Promise<string | null> {
  if (MODO_DEMO) return tokenDemo();
  const { data } = await supabase().auth.getSession();
  return data.session?.access_token ?? null;
}

export async function estaLogado(): Promise<boolean> {
  return (await obterToken()) !== null;
}

export async function sair(): Promise<void> {
  if (MODO_DEMO) {
    try {
      sessionStorage.removeItem(CHAVE_DO_TOKEN_DEMO);
    } catch {
      /* sem armazenamento: nada a limpar */
    }
    avisar("saiu");
    return;
  }
  await supabase().auth.signOut();
}

export function aoMudar(ouvinte: Ouvinte): () => void {
  ouvintes.add(ouvinte);
  if (MODO_DEMO) return () => ouvintes.delete(ouvinte);
  const { data } = supabase().auth.onAuthStateChange((evento) => {
    if (evento === "PASSWORD_RECOVERY") ouvinte("recuperacao");
    else if (evento === "SIGNED_OUT") ouvinte("saiu");
    else if (evento === "SIGNED_IN") ouvinte("entrou");
  });
  return () => {
    ouvintes.delete(ouvinte);
    data.subscription.unsubscribe();
  };
}

// --- modo demo ------------------------------------------------------------------------

export interface UsuarioDeDemo {
  id: string;
  nome: string;
  email: string;
  papel: string;
  organizacao: string;
}

export async function usuariosDeDemo(): Promise<UsuarioDeDemo[]> {
  const resposta = await fetch(`${URL_DA_API}/demo/usuarios`);
  if (!resposta.ok) throw new Error("A API não está em modo demo");
  return (await resposta.json()) as UsuarioDeDemo[];
}

export async function entrarComoDemo(usuarioId: string): Promise<void> {
  const resposta = await fetch(`${URL_DA_API}/demo/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ usuario_id: usuarioId }),
  });
  if (!resposta.ok) throw new Error("Não foi possível entrar no modo demo");
  const { access_token } = (await resposta.json()) as { access_token: string };
  try {
    sessionStorage.setItem(CHAVE_DO_TOKEN_DEMO, access_token);
  } catch {
    throw new Error("O navegador bloqueou o armazenamento da sessão");
  }
  avisar("entrou");
}
