import { IdCard, Lock } from "lucide-react";
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
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-slate-50 px-4">
      <div
        className="pointer-events-none absolute -top-32 left-1/2 h-96 w-[640px] -translate-x-1/2 rounded-full bg-institucional-200/40 blur-3xl"
        aria-hidden="true"
      />
      <div className="relative w-full max-w-sm rounded-2xl border border-slate-200/80 bg-white p-8 shadow-xl shadow-slate-200/70">
        <div className="mb-7 text-center">
          <img src={logoRioUrbe} alt="Prefeitura do Rio — Rio-Urbe" className="mx-auto mb-4 h-auto w-full max-w-[240px]" />
          <p className="text-sm text-slate-500">Sistema de Gestão de Contratos</p>
        </div>

        <form onSubmit={aoEnviar} className="space-y-4">
          <div>
            <label className="field-label" htmlFor="identificador">
              Matrícula ou CPF
            </label>
            <div className="relative">
              <IdCard size={17} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                id="identificador"
                className="field-input pl-9"
                value={identificador}
                onChange={(e) => setIdentificador(e.target.value)}
                autoComplete="username"
                required
              />
            </div>
          </div>
          <div>
            <label className="field-label" htmlFor="senha">
              Senha
            </label>
            <div className="relative">
              <Lock size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                id="senha"
                type="password"
                className="field-input pl-9"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>
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
