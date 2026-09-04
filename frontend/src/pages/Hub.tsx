import { Link } from "react-router-dom";

import { useAuth } from "../lib/AuthContext";

const BLOCOS = [
  {
    titulo: "Contratos",
    descricao: "Gestão de contratos e instrumentos processuais",
    caminho: "/contratos",
  },
  { titulo: "Licitação", descricao: "Pesquisa de preços, ETP, TR e matriz de risco", caminho: null },
  {
    titulo: "Faturas",
    descricao: "Controle de faturas: conferência documental e tributária, atesto e pagamento",
    caminho: "/faturas",
  },
  { titulo: "Diárias, Passagens e Compras", descricao: "Fundo fixo e suprimento de fundos", caminho: null },
  { titulo: "Planejador de Tarefas", descricao: "Quadros Kanban de tarefas do setor", caminho: null },
];

export function Hub() {
  const { usuario } = useAuth();

  return (
    <div className="page-shell">
      <header className="page-header">
        <div>
          <h1 className="page-title">Rio-Urbe — Gestão de Contratos</h1>
          <p className="mt-0.5 text-sm text-slate-500">Olá, {usuario?.nome}</p>
        </div>
      </header>

      <main className="mx-auto grid max-w-5xl grid-cols-1 gap-4 p-6 sm:grid-cols-2 lg:grid-cols-3">
        {BLOCOS.map((bloco) => {
          const conteudo = (
            <>
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
