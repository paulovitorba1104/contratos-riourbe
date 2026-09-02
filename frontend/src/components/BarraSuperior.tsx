import { useAuth } from "../lib/AuthContext";

/** Barra fina, sempre visível, com o usuário logado e o botão Sair — presente
 * em toda tela autenticada (não só no Hub), pra sempre dar pra deslogar. */
export function BarraSuperior() {
  const { usuario, sair } = useAuth();

  if (!usuario) return null;

  return (
    <div className="flex items-center justify-end gap-3 border-b border-institucional-100 bg-institucional-900 px-4 py-1.5 text-xs text-white">
      <span className="text-institucional-100">{usuario.nome}</span>
      <button onClick={sair} className="rounded px-2 py-0.5 font-medium hover:bg-institucional-800">
        Sair
      </button>
    </div>
  );
}
