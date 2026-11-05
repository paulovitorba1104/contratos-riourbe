import { Link } from "react-router-dom";

import { useAuth } from "../lib/AuthContext";
import { ITENS_NAVEGACAO, podeAcessar } from "../lib/navegacao";

export function Hub() {
  const { usuario } = useAuth();
  const blocos = ITENS_NAVEGACAO.filter(
    (item) => item.titulo !== "Início" && (!item.modulo || podeAcessar(usuario, item.modulo)),
  );
  const semModuloLiberado = !blocos.some((bloco) => bloco.caminho);

  return (
    <div className="page-shell">
      <header className="page-header">
        <div>
          <h1 className="page-title">Rio-Urbe — Gestão de Contratos</h1>
          <p className="mt-0.5 text-sm text-slate-500">Olá, {usuario?.nome}</p>
        </div>
      </header>

      {semModuloLiberado && (
        <div className="mx-auto max-w-5xl px-6 pt-6 sm:px-8">
          <div className="card border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            Nenhum módulo foi liberado para você ainda. Peça a um administrador para definir o seu
            acesso.
          </div>
        </div>
      )}

      <main className="mx-auto grid max-w-5xl grid-cols-1 gap-4 p-6 sm:grid-cols-2 sm:p-8 lg:grid-cols-3">
        {blocos.map((bloco) => {
          const Icone = bloco.icone;
          const conteudo = (
            <>
              <span className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-institucional-50 text-institucional-600">
                <Icone size={20} strokeWidth={2} />
              </span>
              <h2 className="mb-1 font-semibold text-slate-900">{bloco.titulo}</h2>
              <p className="text-sm text-slate-500">{bloco.descricao}</p>
              {!bloco.caminho && <span className="pill mt-3 inline-block">Em breve</span>}
            </>
          );

          const classe = "card card-hover block p-5";

          return bloco.caminho ? (
            <Link key={bloco.titulo} to={bloco.caminho} className={classe}>
              {conteudo}
            </Link>
          ) : (
            <div key={bloco.titulo} className={`${classe} opacity-70`}>
              {conteudo}
            </div>
          );
        })}
      </main>
    </div>
  );
}
