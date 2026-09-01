import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { ErroApi } from "../lib/api";
import { useAuth } from "../lib/AuthContext";

export function Login() {
  const { entrar } = useAuth();
  const navegar = useNavigate();
  const [identificador, setIdentificador] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      await entrar(identificador, senha);
      navegar("/");
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível entrar. Tente novamente.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-institucional-50">
      <div className="w-full max-w-sm rounded-lg bg-white p-8 shadow-md">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-institucional-600 text-xl font-bold text-white">
            RU
          </div>
          <h1 className="text-lg font-semibold text-institucional-900">Rio-Urbe</h1>
          <p className="text-sm text-institucional-700">Sistema de Gestão de Contratos</p>
        </div>

        <form onSubmit={aoEnviar} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-institucional-800" htmlFor="identificador">
              Matrícula ou CPF
            </label>
            <input
              id="identificador"
              className="w-full rounded border border-institucional-200 px-3 py-2 text-sm focus:border-institucional-500 focus:outline-none"
              value={identificador}
              onChange={(e) => setIdentificador(e.target.value)}
              autoComplete="username"
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-institucional-800" htmlFor="senha">
              Senha
            </label>
            <input
              id="senha"
              type="password"
              className="w-full rounded border border-institucional-200 px-3 py-2 text-sm focus:border-institucional-500 focus:outline-none"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          {erro && <p className="text-sm text-red-600">{erro}</p>}

          <button
            type="submit"
            disabled={enviando}
            className="w-full rounded bg-institucional-600 py-2 text-sm font-medium text-white transition hover:bg-institucional-700 disabled:opacity-60"
          >
            {enviando ? "Entrando..." : "Entrar"}
          </button>
        </form>
      </div>
    </div>
  );
}
