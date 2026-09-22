import { Menu } from "lucide-react";
import { type ReactNode, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

import { Sidebar } from "./Sidebar";

/** Casco de toda tela autenticada: menu lateral fixo (sempre visível a
 * partir de telas grandes, sobreposto no celular) + coluna de conteúdo. A
 * navegação principal mora aqui, não mais numa barra fininha no topo. */
export function AppShell({ children }: { children: ReactNode }) {
  const [menuAberto, setMenuAberto] = useState(false);
  const { pathname } = useLocation();

  // Fecha o menu mobile sempre que a rota muda (evita ficar aberto por
  // cima da tela seguinte depois de navegar).
  useEffect(() => {
    setMenuAberto(false);
  }, [pathname]);

  return (
    <div className="min-h-screen bg-slate-50">
      <Sidebar aberto={menuAberto} aoFechar={() => setMenuAberto(false)} />

      <div className="flex min-h-screen flex-col lg:pl-64">
        <div className="sticky top-0 z-20 flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
          <button
            onClick={() => setMenuAberto(true)}
            className="rounded-md p-1.5 text-slate-600 hover:bg-slate-100"
            aria-label="Abrir menu"
          >
            <Menu size={20} />
          </button>
          <span className="text-sm font-semibold text-slate-900">Rio-Urbe</span>
        </div>

        <main className="flex-1">{children}</main>
      </div>
    </div>
  );
}
