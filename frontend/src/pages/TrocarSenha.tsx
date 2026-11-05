import { KeyRound } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { api, ErroApi } from "../lib/api";
import { useAuth } from "../lib/AuthContext";
import { useToast } from "../lib/ToastContext";

const REGRAS = [
  "Mínimo de 10 caracteres",
  "Pelo menos 3 destes 4 tipos: minúscula, maiúscula, número, símbolo",
  "Diferente da senha atual",
];

function Formulario({ obrigatoria }: { obrigatoria: boolean }) {
  const { atualizarUsuario, sair } = useAuth();
  const { mostrarToast } = useToast();
  const navegar = useNavigate();
  const [senhaAtual, setSenhaAtual] = useState("");
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    if (novaSenha !== confirmacao) {
      setErro("A confirmação não confere com a nova senha.");
      return;
    }
    setEnviando(true);
    try {
      const usuario = await api.trocarSenha(senhaAtual, novaSenha);
      atualizarUsuario(usuario);
      mostrarToast("Senha alterada com sucesso.");
      if (obrigatoria) {
        navegar("/", { replace: true });
      } else {
        setSenhaAtual("");
        setNovaSenha("");
        setConfirmacao("");
      }
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível trocar a senha.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={aoEnviar} className="space-y-4">
      <div>
        <label className="field-label" htmlFor="senha_atual">
          {obrigatoria ? "Senha temporária" : "Senha atual"}
        </label>
        <input
          id="senha_atual"
          type="password"
          className="field-input"
          value={senhaAtual}
          onChange={(e) => setSenhaAtual(e.target.value)}
          autoComplete="current-password"
          required
        />
      </div>
      <div>
        <label className="field-label" htmlFor="nova_senha">
          Nova senha
        </label>
        <input
          id="nova_senha"
          type="password"
          className="field-input"
          value={novaSenha}
          onChange={(e) => setNovaSenha(e.target.value)}
          autoComplete="new-password"
          required
        />
      </div>
      <div>
        <label className="field-label" htmlFor="confirmacao_senha">
          Confirme a nova senha
        </label>
        <input
          id="confirmacao_senha"
          type="password"
          className="field-input"
          value={confirmacao}
          onChange={(e) => setConfirmacao(e.target.value)}
          autoComplete="new-password"
          required
        />
      </div>
      <ul className="list-disc space-y-0.5 pl-5 text-xs text-slate-500">
        {REGRAS.map((regra) => (
          <li key={regra}>{regra}</li>
        ))}
      </ul>

      {erro && <p className="text-sm text-red-600">{erro}</p>}

      <div className="flex flex-col gap-2">
        <button type="submit" disabled={enviando} className="btn-primary w-full py-2.5">
          {enviando ? "Salvando..." : "Salvar nova senha"}
        </button>
        {obrigatoria && (
          <button type="button" onClick={sair} className="btn-secondary w-full">
            Sair
          </button>
        )}
      </div>
    </form>
  );
}

/** Troca de senha pelo próprio usuário. Quando a senha atual é temporária
 * (gerada por um administrador ou pelo script de resgate no servidor), esta é
 * a única tela liberada — aparece sozinha, fora do menu, até a troca. */
export function TrocarSenha() {
  const { usuario } = useAuth();
  const obrigatoria = Boolean(usuario?.trocar_senha_obrigatorio);

  if (obrigatoria) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <div className="w-full max-w-sm rounded-2xl border border-slate-200/80 bg-white p-8 shadow-xl shadow-slate-200/70">
          <div className="mb-6 text-center">
            <span className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-institucional-50 text-institucional-600">
              <KeyRound size={20} />
            </span>
            <h1 className="text-lg font-semibold text-slate-900">Crie uma senha nova</h1>
            <p className="mt-1 text-sm text-slate-500">
              Você entrou com uma senha temporária. Para continuar, escolha uma senha só sua.
            </p>
          </div>
          <Formulario obrigatoria />
        </div>
      </div>
    );
  }

  return (
    <div className="page-shell">
      <header className="page-header">
        <h1 className="page-title">Trocar senha</h1>
      </header>
      <main className="mx-auto max-w-md p-6">
        <div className="card p-5">
          <Formulario obrigatoria={false} />
        </div>
      </main>
    </div>
  );
}
