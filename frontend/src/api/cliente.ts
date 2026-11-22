import createClient, { type Middleware } from "openapi-fetch";

import { supabase } from "../supabase";
import type { paths } from "./schema";

// Toda chamada à API leva o token da sessão do Supabase.
const autenticacao: Middleware = {
  async onRequest({ request }) {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (token) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
    return request;
  },
};

export const api = createClient<paths>({
  baseUrl: (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000",
});
api.use(autenticacao);
