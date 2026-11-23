import { useEu } from "../eu";
import { NOMES_DOS_PAPEIS } from "../ui";

export { NOMES_DOS_PAPEIS };

export function MinhaOrganizacao() {
  const { eu } = useEu();
  if (!eu) return null;

  return (
    <>
      <header className="cabecalho">
        <div>
          <p className="rotulo">{eu.organizacao.nome}</p>
          <h1>Meu perfil</h1>
        </div>
      </header>
      <section className="painel" style={{ maxWidth: 560 }}>
        <dl className="dados">
          <dt>Nome</dt>
          <dd>{eu.nome}</dd>
          <dt>E-mail</dt>
          <dd>{eu.email}</dd>
          <dt>Papel</dt>
          <dd>{NOMES_DOS_PAPEIS[eu.papel] ?? eu.papel}</dd>
          <dt>Organização</dt>
          <dd>{eu.organizacao.nome}</dd>
        </dl>
      </section>
    </>
  );
}
