import { Landmark, LogOut, X } from "lucide-react";
import { Link, useLocation } from "react-router-dom";

import { useAuth } from "../lib/AuthContext";
import { ITENS_NAVEGACAO } from "../lib/navegacao";

function ehAtivo(caminhoAtual: string, caminho: string): boolean {
  if (caminho === "/") return caminhoAtual === "/";
  return caminhoAtual === caminho || caminhoAtual.startsWith(`${caminho}/`);
}

function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/);
  const primeira = partes[0]?.[0] ?? "";
  const ultima = partes.length > 1 ? partes[partes.length - 1][0] : "";
  return (primeira + ultima).toUpperCase();
}

export function Sidebar({ aberto, aoFechar }: { aberto: boolean; aoFechar: () => void }) {
  const { usuario, sair } = useAuth();
  const { pathname } = useLocation();

  if (!usuario) return null;

  return (
    <>
      {/* Fundo escurecido — só no mobile, quando o menu está aberto */}
      {aberto && (
        <div
          className="fixed inset-0 z-30 bg-slate-900/50 lg:hidden"
          onClick={aoFechar}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex h-full w-64 flex-col bg-institucional-950 transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          aberto ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between gap-2 px-5 py-5">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-institucional-500/20 text-institucional-200">
              <Landmark size={18} strokeWidth={2} />
            </span>
            <div className="leading-tight">
              <p className="text-sm font-semibold text-white">Rio-Urbe</p>
              <p className="text-[11px] text-institucional-300">Gestão de Contratos</p>
            </div>
          </div>
          <button
            onClick={aoFechar}
            className="rounded-md p-1 text-institucional-300 hover:bg-white/10 hover:text-white lg:hidden"
            aria-label="Fechar menu"
          >
            <X size={18} />
          </button>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-2">
          {ITENS_NAVEGACAO.map((item) => {
            const Icone = item.icone;
            if (!item.caminho) {
              return (
                <div
                  key={item.titulo}
                  className="flex items-start gap-3 rounded-lg px-3 py-2 text-sm text-institucional-400/70"
                  title={item.descricao}
                >
                  <Icone size={17} strokeWidth={2} className="mt-0.5 shrink-0" />
                  <span className="flex-1 leading-snug">{item.titulo}</span>
                  <span className="mt-0.5 shrink-0 rounded-full bg-white/5 px-1.5 py-0.5 text-[10px] font-medium text-institucional-300">
                    em breve
                  </span>
                </div>
              );
            }
            const ativo = ehAtivo(pathname, item.caminho);
            return (
              <Link
                key={item.titulo}
                to={item.caminho}
                onClick={aoFechar}
                className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium leading-snug transition ${
                  ativo
                    ? "bg-white text-institucional-900 shadow-sm"
                    : "text-institucional-100 hover:bg-white/10"
                }`}
              >
                <Icone size={17} strokeWidth={2} className="shrink-0" />
                <span>{item.titulo}</span>
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-white/10 px-3 py-3">
          <div className="flex items-center gap-2.5 rounded-lg px-2 py-2">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-institucional-500/25 text-xs font-semibold text-white">
              {iniciais(usuario.nome)}
            </span>
            <div className="min-w-0 flex-1 leading-tight">
              <p className="truncate text-sm font-medium text-white">{usuario.nome}</p>
              <p className="truncate text-[11px] capitalize text-institucional-300">{usuario.papel}</p>
            </div>
            <button
              onClick={sair}
              className="rounded-md p-1.5 text-institucional-300 transition hover:bg-white/10 hover:text-white"
              title="Sair"
              aria-label="Sair"
            >
              <LogOut size={16} />
            </button>
          </div>
          <p className="mt-2 px-2 text-[10px] text-institucional-400/60">
            Since 2026 — Desenvolvido por Paulo Vitor Barbosa Araújo
          </p>
        </div>
      </aside>
    </>
  );
}
