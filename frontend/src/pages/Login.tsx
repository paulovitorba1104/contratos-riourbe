import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import logoRioUrbe from "../assets/logo-rio-urbe.png";
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
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-8 shadow-lg shadow-slate-200/60">
        <div className="mb-7 text-center">
          <img src={logoRioUrbe} alt="Prefeitura do Rio — Rio-Urbe" className="mx-auto mb-4 h-auto w-full max-w-[240px]" />
          <p className="text-sm text-slate-500">Sistema de Gestão de Contratos</p>
        </div>

        <form onSubmit={aoEnviar} className="space-y-4">
          <div>
            <label className="field-label" htmlFor="identificador">
              Matrícula ou CPF
            </label>
            <input
              id="identificador"
              className="field-input"
              value={identificador}
              onChange={(e) => setIdentificador(e.target.value)}
              autoComplete="username"
              required
            />
          </div>
          <div>
            <label className="field-label" htmlFor="senha">
              Senha
            </label>
            <input
              id="senha"
              type="password"
              className="field-input"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          {erro && <p className="text-sm text-red-600">{erro}</p>}

          <button type="submit" disabled={enviando} className="btn-primary w-full py-2.5">
            {enviando ? "Entrando..." : "Entrar"}
          </button>
        </form>
      </div>
    </div>
  );
}
