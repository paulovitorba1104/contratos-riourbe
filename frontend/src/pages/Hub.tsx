import { useAuth } from "../lib/AuthContext";

const BLOCOS = [
  { titulo: "Contratos", descricao: "Gestão de contratos e instrumentos processuais" },
  { titulo: "Licitação", descricao: "Pesquisa de preços, ETP, TR e matriz de risco" },
  { titulo: "Faturas", descricao: "Atesto, liquidação e conferência de notas fiscais" },
  { titulo: "Diárias, Passagens e Compras", descricao: "Fundo fixo e suprimento de fundos" },
  { titulo: "Planejador de Tarefas", descricao: "Quadros Kanban de tarefas do setor" },
];

export function Hub() {
  const { usuario, sair } = useAuth();

  return (
    <div className="min-h-screen bg-institucional-50 pb-16">
      <header className="flex items-center justify-between border-b border-institucional-100 bg-white px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold text-institucional-900">Rio-Urbe — Gestão de Contratos</h1>
          <p className="text-sm text-institucional-700">Olá, {usuario?.nome}</p>
        </div>
        <button
          onClick={sair}
          className="rounded border border-institucional-300 px-3 py-1.5 text-sm text-institucional-700 hover:bg-institucional-100"
        >
          Sair
        </button>
      </header>

      <main className="mx-auto grid max-w-5xl grid-cols-1 gap-4 p-6 sm:grid-cols-2 lg:grid-cols-3">
        {BLOCOS.map((bloco) => (
          <div
            key={bloco.titulo}
            className="rounded-lg border border-institucional-100 bg-white p-5 shadow-sm transition hover:shadow-md"
          >
            <h2 className="mb-1 font-semibold text-institucional-900">{bloco.titulo}</h2>
            <p className="text-sm text-institucional-700">{bloco.descricao}</p>
          </div>
        ))}
      </main>
    </div>
  );
}
