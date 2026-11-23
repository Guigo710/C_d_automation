import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let cliente: SupabaseClient | null = null;

// Criado só quando usado, para o modo demo funcionar sem projeto no Supabase.
export function supabase(): SupabaseClient {
  if (!cliente) {
    const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
    const chave = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;
    if (!url || !chave) {
      throw new Error("Defina VITE_SUPABASE_URL e VITE_SUPABASE_ANON_KEY no frontend/.env");
    }
    cliente = createClient(url, chave);
  }
  return cliente;
}
