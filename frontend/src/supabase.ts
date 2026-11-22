import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const chave = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

if (!url || !chave) {
  throw new Error("Defina VITE_SUPABASE_URL e VITE_SUPABASE_ANON_KEY no frontend/.env");
}

export const supabase = createClient(url, chave);
