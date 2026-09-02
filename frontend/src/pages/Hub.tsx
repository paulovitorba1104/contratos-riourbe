import { Link } from "react-router-dom";

import { useAuth } from "../lib/AuthContext";

const BLOCOS = [
  {
    titulo: "Contratos",
    descricao: "Gestão de contratos e instrumentos processuais",
    caminho: "/contratos",
  },
  { titulo: "Licitação", descricao: "Pesquisa de preços, ETP, TR e matriz de risco", caminho: null },
  { titulo: "Faturas", descricao: "Atesto, liquidação e conferência de notas fiscais", caminho: null },
  { titulo: "Diárias, Passagens e Compras", descricao: "Fundo fixo e suprimento de fundos", caminho: null },
  { titulo: "Planejador de Tarefas", descricao: "Quadros Kanban de tarefas do setor", caminho: null },
];

export function Hub() {
  const { usuario } = useAuth();

  return (
    <div className="min-h-screen bg-institucional-50 pb-16">
      <header className="border-b border-institucional-100 bg-white px-6 py-4">
        <h1 className="text-lg font-semibold text-institucional-900">Rio-Urbe — Gestão de Contratos</h1>
        <p className="text-sm text-institucional-700">Olá, {usuario?.nome}</p>
      </header>

      <main className="mx-auto grid max-w-5xl grid-cols-1 gap-4 p-6 sm:grid-cols-2 lg:grid-cols-3">
        {BLOCOS.map((bloco) => {
          const conteudo = (
            <>
              <h2 className="mb-1 font-semibold text-institucional-900">{bloco.titulo}</h2>
              <p className="text-sm text-institucional-700">{bloco.descricao}</p>
              {!bloco.caminho && <p className="mt-2 text-xs text-institucional-400">Em breve</p>}
            </>
          );

          const classe =
            "rounded-lg border border-institucional-100 bg-white p-5 shadow-sm transition hover:shadow-md";

          return bloco.caminho ? (
            <Link key={bloco.titulo} to={bloco.caminho} className={`block ${classe}`}>
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
