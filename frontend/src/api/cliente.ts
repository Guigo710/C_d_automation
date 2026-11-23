import createClient, { type Middleware } from "openapi-fetch";

import { obterToken } from "../autenticacao";
import type { paths } from "./schema";

// Toda chamada à API leva o token da sessão do Supabase.
const autenticacao: Middleware = {
  async onRequest({ request }) {
    const token = await obterToken();
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
