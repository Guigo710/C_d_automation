import { useEu } from "../eu";

export const NOMES_DOS_PAPEIS: Record<string, string> = {
  administrador: "Administrador",
  coordenador: "Coordenador",
  vendedor: "Vendedor",
};

export function MinhaOrganizacao() {
  const { eu } = useEu();
  if (!eu) return null;

  return (
    <section className="painel">
      <p className="rotulo">Organização</p>
      <h1>{eu.organizacao.nome}</h1>
      <dl>
        <dt>Usuário</dt>
        <dd>{eu.nome}</dd>
        <dt>E-mail</dt>
        <dd>{eu.email}</dd>
        <dt>Papel</dt>
        <dd>{NOMES_DOS_PAPEIS[eu.papel] ?? eu.papel}</dd>
      </dl>
    </section>
  );
}
