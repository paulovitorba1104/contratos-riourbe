import { CheckCircle2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router-dom";

import logoRioUrbe from "../assets/logo-rio-urbe.png";
import { api, ErroApi } from "../lib/api";
import { useAuth } from "../lib/AuthContext";
import { mascararCpf } from "../lib/mascaras";

/** Pedido de acesso feito pelo próprio usuário. A conta só funciona depois que
 * um administrador aprova e define os módulos. */
export function Cadastro() {
  const { usuario } = useAuth();
  const [nome, setNome] = useState("");
  const [matricula, setMatricula] = useState("");
  const [cpf, setCpf] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [enviado, setEnviado] = useState(false);

  if (usuario) {
    return <Navigate to="/" replace />;
  }

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    if (senha !== confirmacao) {
      setErro("A confirmação não confere com a senha.");
      return;
    }
    setEnviando(true);
    try {
      await api.solicitarCadastro({ nome, matricula, cpf, email, senha });
      setEnviado(true);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível enviar o pedido.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-10">
      <div className="w-full max-w-md rounded-2xl border border-slate-200/80 bg-white p-8 shadow-xl shadow-slate-200/70">
        <div className="mb-6 text-center">
          <img src={logoRioUrbe} alt="Prefeitura do Rio — Rio-Urbe" className="mx-auto mb-4 h-auto w-full max-w-[220px]" />
          <h1 className="text-lg font-semibold text-slate-900">Solicitar acesso</h1>
          <p className="mt-1 text-sm text-slate-500">
            Um administrador analisa o pedido e define quais módulos você vai usar.
          </p>
        </div>

        {enviado ? (
          <div className="space-y-4 text-center">
            <CheckCircle2 size={36} className="mx-auto text-emerald-600" />
            <p className="text-sm text-slate-700">
              Pedido enviado. Você poderá entrar com a sua matrícula ou CPF assim que um administrador
              aprovar o seu acesso.
            </p>
            <Link to="/login" className="btn-primary inline-flex w-full justify-center py-2.5">
              Voltar para o login
            </Link>
          </div>
        ) : (
          <form onSubmit={aoEnviar} className="space-y-4">
            <div>
              <label className="field-label" htmlFor="cad_nome">
                Nome completo
              </label>
              <input
                id="cad_nome"
                className="field-input"
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                autoComplete="name"
                required
              />
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="field-label" htmlFor="cad_matricula">
                  Matrícula
                </label>
                <input
                  id="cad_matricula"
                  className="field-input"
                  value={matricula}
                  onChange={(e) => setMatricula(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="field-label" htmlFor="cad_cpf">
                  CPF
                </label>
                <input
                  id="cad_cpf"
                  className="field-input"
                  value={cpf}
                  onChange={(e) => setCpf(mascararCpf(e.target.value))}
                  placeholder="000.000.000-00"
                  inputMode="numeric"
                  required
                />
              </div>
            </div>
            <p className="-mt-2 text-xs text-slate-500">
              No login vale a matrícula exatamente como digitada aqui, ou o CPF.
            </p>
            <div>
              <label className="field-label" htmlFor="cad_email">
                E-mail institucional
              </label>
              <input
                id="cad_email"
                type="email"
                className="field-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="field-label" htmlFor="cad_senha">
                  Senha
                </label>
                <input
                  id="cad_senha"
                  type="password"
                  className="field-input"
                  value={senha}
                  onChange={(e) => setSenha(e.target.value)}
                  autoComplete="new-password"
                  required
                />
              </div>
              <div>
                <label className="field-label" htmlFor="cad_confirmacao">
                  Confirme a senha
                </label>
                <input
                  id="cad_confirmacao"
                  type="password"
                  className="field-input"
                  value={confirmacao}
                  onChange={(e) => setConfirmacao(e.target.value)}
                  autoComplete="new-password"
                  required
                />
              </div>
            </div>
            <p className="-mt-2 text-xs text-slate-500">
              Mínimo de 10 caracteres, com pelo menos 3 destes tipos: minúscula, maiúscula, número,
              símbolo.
            </p>

            {erro && <p className="text-sm text-red-600">{erro}</p>}

            <button type="submit" disabled={enviando} className="btn-primary w-full py-2.5">
              {enviando ? "Enviando..." : "Enviar pedido"}
            </button>
            <p className="text-center text-sm text-slate-500">
              Já tem acesso?{" "}
              <Link to="/login" className="text-institucional-600 hover:underline">
                Entrar
              </Link>
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
